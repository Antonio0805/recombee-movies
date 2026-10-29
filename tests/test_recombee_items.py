"""Verificări locale: lotul final, eșecuri parțiale și citirea catalogului."""

import copy
import unittest
from unittest.mock import Mock, patch

from recombee_items import CatalogNotReady, prepare_items, send_items, verify_items, verify_with_retry
from recombee_properties import load_dataset


class ItemImportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.items = prepare_items(load_dataset())

    def test_mapping_and_python_types(self):
        item = self.items[0]
        self.assertEqual(item["itemId"], "19995")
        self.assertNotIn("id", item["values"])
        self.assertNotIn("itemId", item["values"])
        self.assertEqual(item["values"]["title"], "Avatar")
        self.assertIs(type(item["values"]["revenue"]), int)
        self.assertIs(type(item["values"]["popularity"]), float)

    def test_real_catalog_49_batches_including_last_3(self):
        client = Mock()
        client.send.side_effect = lambda batch: [{"code": 200} for _ in batch.requests]
        self.assertEqual(send_items(client, self.items), 49)
        sizes = [len(call.args[0].requests) for call in client.send.call_args_list]
        self.assertEqual(sizes, [100] * 48 + [3])
        request = client.send.call_args_list[0].args[0].requests[0]
        self.assertIs(request.get_body_parameters()["!cascadeCreate"], True)

    def test_partial_error_stops_even_when_batch_call_succeeds(self):
        client = Mock()
        client.send.return_value = [{"code": 200}, {"code": 400}]
        with self.assertRaisesRegex(ValueError, "1 cereri au eșuat"):
            send_items(client, self.items[:2])

    def test_truncated_batch_response_is_not_success(self):
        client = Mock()
        client.send.return_value = [{"code": 200}]
        with self.assertRaisesRegex(ValueError, "incomplet"):
            send_items(client, self.items[:2])

    def test_verification_checks_every_page_and_all_attributes(self):
        pages = [[dict(itemId=i["itemId"], **i["values"])] for i in self.items[:2]]
        client = Mock()
        client.send.side_effect = pages + [[]]
        result = verify_items(client, self.items[:2])
        self.assertEqual(result["verified_items"], 2)
        self.assertEqual(client.send.call_args_list[1].args[0].get_query_parameters()["offset"], 1)

    def test_wrong_remote_value_is_detected(self):
        remote = dict(itemId=self.items[0]["itemId"], **copy.deepcopy(self.items[0]["values"]))
        remote["revenue"] += 1
        client = Mock()
        client.send.return_value = [remote]
        with self.assertRaisesRegex(ValueError, "proprietate=revenue"):
            verify_items(client, self.items[:1])

    def test_missing_movie_is_detected(self):
        client = Mock()
        client.send.return_value = []
        with self.assertRaisesRegex(ValueError, "Lipsesc 1"):
            verify_items(client, self.items[:1])

    def test_unknown_remote_item_is_preserved_and_counted(self):
        item = self.items[0]
        client = Mock()
        client.send.side_effect = [[dict(itemId=item["itemId"], **item["values"]),
                                    {"itemId": "other-movie"}], []]
        self.assertEqual(verify_items(client, [item])["extra_items"], 1)

    def test_catalog_still_updating_is_read_again(self):
        with patch("recombee_items.verify_items", side_effect=[CatalogNotReady(), {"verified_items": 1}]), \
                patch("recombee_items.time.sleep") as sleep:
            self.assertEqual(verify_with_retry(Mock(), self.items[:1]), {"verified_items": 1})
            sleep.assert_called_once_with(2)

    def test_retry_has_finite_limit(self):
        with patch("recombee_items.verify_items", side_effect=CatalogNotReady()), \
                patch("recombee_items.time.sleep"):
            with self.assertRaises(CatalogNotReady):
                verify_with_retry(Mock(), self.items[:1])


if __name__ == "__main__":
    unittest.main()
