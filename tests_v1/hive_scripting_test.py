import json
import sys
import time
import unittest
import logging
from flask import appcontext_pushed, g
from contextlib import contextmanager
# from hive import create_app, HIVE_MODE_TEST
from hive.util.constants import HIVE_MODE_TEST
from src import create_app
from tests_v1 import test_common
from tests_v1.test_common import did

logger = logging.getLogger()
logger.level = logging.DEBUG


@contextmanager
def name_set(app, name):
    def handler(sender, **kwargs):
        g.app_name = name

    with appcontext_pushed.connected_to(handler, app):
        yield


class HiveMongoScriptingTestCase(unittest.TestCase):
    def __init__(self, methodName='runTest'):
        super(HiveMongoScriptingTestCase, self).__init__(methodName)

    @classmethod
    def setUpClass(cls):
        cls.stream_handler = logging.StreamHandler(sys.stdout)
        logger.addHandler(cls.stream_handler)
        logging.getLogger("HiveMongoScriptingTestCase").debug("Setting up HiveMongoScriptingTestCase\n")

    @classmethod
    def tearDownClass(cls):
        logging.getLogger("HiveMongoScriptingTestCase").debug("\n\nShutting down HiveMongoScriptingTestCase")
        logger.removeHandler(cls.stream_handler)

    def setUp(self):
        logging.getLogger("HiveMongoScriptingTestCase").info("\n")
        self.app = create_app(mode=HIVE_MODE_TEST)
        self.app.config['TESTING'] = True
        self.test_client = self.app.test_client()
        self.content_type = ("Content-Type", "application/json")

        self.json_header = [
            self.content_type,
        ]
        test_common.setup_test_auth_token()
        self.init_auth()
        self.did = test_common.get_auth_did()
        self.app_id = test_common.get_auth_app_did()
        test_common.setup_test_vault(self.did)
        self.init_collection_for_test()

    def init_auth(self):
        token = test_common.get_auth_token()
        self.auth = [
            ("Authorization", "token " + token),
            self.content_type,
        ]

    def tearDown(self):
        test_common.delete_test_auth_token()
        logging.getLogger("HiveMongoScriptingTestCase").info("\n")

    def init_db(self):
        pass

    def parse_response(self, r):
        try:
            logging.getLogger("HiveMongoScriptingTestCase").debug("\nret:" + str(r.get_data()))
            v = json.loads(r.get_data())
        except json.JSONDecodeError:
            v = None
        return v, r.status_code

    def assert200(self, status):
        self.assertEqual(status, 200)

    def assert201(self, status):
        self.assertEqual(status, 201)

    def init_collection_for_test(self):
        logging.getLogger("HiveMongoDbTestCase").debug("\nRunning init_collection_for_test")
        r, s = self.parse_response(
            self.test_client.post('/api/v1/db/create_collection',
                                  data=json.dumps(
                                      {
                                          "collection": "groups"
                                      }
                                  ),
                                  headers=self.auth)
        )
        self.assert200(s)
        self.assertEqual(r["_status"], "OK")

        r, s = self.parse_response(
            self.test_client.post('/api/v1/db/insert_one',
                                  data=json.dumps(
                                      {
                                          "collection": "groups",
                                          "document": {
                                              "friends": "did:elastos:ijUnD4KeRpeBUFmcEDCbhxMTJRzUYCQCZM",
                                          }
                                      }
                                  ),
                                  headers=self.auth)
        )
        self.assert200(s)
        self.assertEqual(r["_status"], "OK")

    def test_1_set_script_without_condition(self):
        logging.getLogger("HiveMongoScriptingTestCase").debug("\nRunning test_1_set_script_without_condition")
        r, s = self.parse_response(
            self.test_client.post('/api/v1/scripting/set_script',
                                  data=json.dumps(
                                      {
                                          "name": "script_no_condition",
                                          "executable": {
                                              "type": "find",
                                              "name": "get_groups",
                                              "body": {
                                                  "collection": "groups",
                                                  "filter": {
                                                      "friends": "$caller_did"
                                                  }
                                              }
                                          }
                                      }
                                  ),
                                  headers=self.auth)
        )
        self.assert200(s)
        self.assertEqual(r["_status"], "OK")

    def test_2_set_script_with_condition(self):
        logging.getLogger("HiveMongoScriptingTestCase").debug("\nRunning test_2_set_script_with_condition")
        r, s = self.parse_response(
            self.test_client.post('/api/v1/scripting/set_script',
                                  data=json.dumps(
                                      {
                                          "name": "script_condition",
                                          "executable": {
                                              "type": "find",
                                              "name": "get_groups",
                                              "body": {
                                                  "collection": "test_group",
                                                  "filter": {
                                                      "friends": "$caller_did"
                                                  }
                                              }
                                          },
                                          "condition": {
                                              "type": "queryHasResults",
                                              "name": "verify_user_permission",
                                              "body": {
                                                  "collection": "test_group",
                                                  "filter": {
                                                      "_id": "$params.group_id",
                                                      "friends": "$caller_did"
                                                  }
                                              }
                                          }
                                      }
                                  ),
                                  headers=self.auth)
        )
        self.assert200(s)
        self.assertEqual(r["_status"], "OK")

    def test_3_set_script_with_complex_condition(self):
        logging.getLogger("HiveMongoScriptingTestCase").debug("\nRunning test_3_set_script_with_complex_condition")
        r, s = self.parse_response(
            self.test_client.post('/api/v1/scripting/set_script',
                                  data=json.dumps(
                                      {
                                          "name": "script_complex_condition",
                                          "executable": {
                                              "type": "find",
                                              "name": "get_groups",
                                              "body": {
                                                  "collection": "test_group",
                                                  "filter": {
                                                      "friends": "$caller_did"
                                                  }
                                              }
                                          },
                                          "condition": {
                                              "type": "and",
                                              "name": "verify_user_permission",
                                              "body": [
                                                  {
                                                      "type": "queryHasResults",
                                                      "name": "user_in_group",
                                                      "body": {
                                                          "collection": "test_group",
                                                          "filter": {
                                                              "_id": "$params.group_id",
                                                              "friends": "$caller_did"
                                                          }
                                                      }
                                                  },
                                                  {
                                                      "type": "queryHasResults",
                                                      "name": "user_in_group",
                                                      "body": {
                                                          "collection": "test_group",
                                                          "filter": {
                                                              "_id": "$params.group_id",
                                                              "friends": "$caller_did"
                                                          }
                                                      }
                                                  }
                                              ]
                                          }
                                      }
                                  ),
                                  headers=self.auth)
        )
        self.assert200(s)
        self.assertEqual(r["_status"], "OK")

    def test_4_set_script_with_anonymous_access(self):
        logging.getLogger("HiveMongoScriptingTestCase").debug("\nRunning test_4_set_script_with_anonymous_access")
        r, s = self.parse_response(
            self.test_client.post('/api/v1/scripting/set_script',
                                  data=json.dumps(
                                      {
                                          "name": "script_anonymous_access",
                                          "allowAnonymousUser": True,
                                          "allowAnonymousApp": True,
                                          "executable": {
                                              "type": "find",
                                              "name": "get_all_groups",
                                              "body": {
                                                  "collection": "groups"
                                              }
                                          }
                                      }
                                  ),
                                  headers=self.auth)
        )
        self.assert200(s)
        self.assertEqual(r["_status"], "OK")

    def test_5_run_script_without_condition(self):
        logging.getLogger("HiveMongoScriptingTestCase").debug("\nRunning test_4_run_script_without_condition")
        r, s = self.parse_response(
            self.test_client.post('/api/v1/scripting/run_script',
                                  data=json.dumps(
                                      {
                                          "name": "script_no_condition"
                                      }
                                  ),
                                  headers=self.auth)
        )
        self.assert200(s)
        self.assertEqual(r["_status"], "OK")

    def test_5_1_run_other_user_script_without_condition(self):
        logging.getLogger("HiveMongoScriptingTestCase").debug(
            "\nRunning test_4_1_run_other_user_script_without_condition")

        token = test_common.get_auth_token2()
        auth = [
            ("Authorization", "token " + token),
            self.content_type,
        ]

        r, s = self.parse_response(
            self.test_client.post('/api/v1/scripting/run_script',
                                  data=json.dumps(
                                      {
                                          "name": "script_no_condition",
                                          "context": {
                                              "target_did": test_common.did,
                                              "target_app_did": test_common.app_id
                                          }
                                      }
                                  ),
                                  headers=auth)
        )
        self.assert200(s)
        self.assertEqual(r["_status"], "OK")

    def test_6_run_script_with_condition(self):
        logging.getLogger("HiveMongoScriptingTestCase").debug("\nRunning test_5_run_script_with_condition")

        # Set up the pre-requisites to run this test
        self.test_client.post('/api/v1/db/create_collection',
                              data=json.dumps({"collection": "test_group"}),
                              headers=self.auth)
        r, s = self.parse_response(self.test_client.post('/api/v1/db/insert_one',
                                                         data=json.dumps({"collection": "test_group",
                                                                          "document": {"name": "Trinity",
                                                                                       "friends": [did]}}),
                                                         headers=self.auth))
        self.assert200(s)
        self.assertEqual(r["_status"], "OK")

        # Run the actual test
        group_id = r["inserted_id"]
        r, s = self.parse_response(
            self.test_client.post('/api/v1/scripting/run_script',
                                  data=json.dumps(
                                      {
                                          "name": "script_condition",
                                          "params": {
                                              "group_id": {"$oid": group_id}
                                          }
                                      }
                                  ),
                                  headers=self.auth)
        )
        self.assert200(s)
        self.assertEqual(r["_status"], "OK")

        # Tear down
        self.test_client.post('/api/v1/db/delete_collection',
                              data=json.dumps({"collection": "test_group"}),
                              headers=self.auth)

    def test_7_run_script_with_anonymous_access(self):
        logging.getLogger("HiveMongoScriptingTestCase").debug("\nRunning test_4_run_script_with_anonymous_access")
        r, s = self.parse_response(
            self.test_client.post('/api/v1/scripting/run_script',
                                  data=json.dumps(
                                      {
                                          "name": "script_anonymous_access",
                                          "context": {
                                              "target_did": "did:elastos:ij8krAVRJitZKJmcCufoLHQjq7Mef3ZjTN",
                                              "target_app_did": "appid"
                                          },
                                      }
                                  ))
        )
        self.assert200(s)
        self.assertEqual(r["_status"], "OK")

    def test_8_run_script_with_url(self):
        logging.getLogger("HiveMongoScriptingTestCase").debug("\nRunning test_8_run_script_with_url")
        r, s = self.parse_response(
            self.test_client.get('/api/v1/scripting/run_script_url/'
                                 'did:elastos:ij8krAVRJitZKJmcCufoLHQjq7Mef3ZjTN@appid/'
                                 'script_anonymous_access')
        )
        self.assert200(s)
        self.assertEqual(r["_status"], "OK")

    def test01_upload_file(self):
        logging.getLogger("HiveMongoScriptingTestCase").debug("\nRunning test01_upload_file")
        file_path, script_name = 'scripting/test_01.txt', "script_upload_file"
        file_content, executable_name = f'{file_path} content 12345678', 'upload_file'
        r, s = self.parse_response(
            self.test_client.post('/api/v1/scripting/set_script',
                                  data=json.dumps(
                                      {
                                          "name": script_name,
                                          "allowAnonymousUser": True,
                                          "allowAnonymousApp": True,
                                          "executable": {
                                              "output": True,
                                              "name": executable_name,
                                              "type": "fileUpload",
                                              "body": {
                                                  "path": "$params.path"
                                              }
                                          }
                                      }
                                  ),
                                  headers=self.auth)
        )
        self.assert200(s)
        self.assertEqual(r["_status"], "OK")
        r, s = self.parse_response(
            self.test_client.post('/api/v1/scripting/run_script',
                                  data=json.dumps(
                                      {
                                          "name": script_name,
                                          "context": {
                                              "target_did": "did:elastos:ij8krAVRJitZKJmcCufoLHQjq7Mef3ZjTN",
                                              "target_app_did": "appid"
                                          },
                                          'params': {
                                              'path': file_path
                                          }
                                      }
                                  ))
        )
        self.assert200(s)
        self.assertEqual(r["_status"], "OK")
        transaction_id = r[executable_name]['transaction_id']
        r, s = self.parse_response(
            self.test_client.post(f'/api/v1/scripting/run_script_upload/{transaction_id}',
                                  data=file_content)
        )
        self.assert200(s)
        self.assertEqual(r["_status"], "OK")

    def test02_upload_file_by_url(self):
        logging.getLogger("HiveMongoScriptingTestCase").debug("\nRunning test02_upload_file_by_url")
        file_path = 'scripting/test_02.txt'
        r, s = self.parse_response(
            self.test_client.post('/api/v1/scripting/set_script',
                                  data=json.dumps(
                                      {
                                          "name": "script_upload_file",
                                          "allowAnonymousUser": True,
                                          "allowAnonymousApp": True,
                                          "executable": {
                                              "output": True,
                                              "name": 'upload_file',
                                              "type": "fileUpload",
                                              "body": {
                                                  "path": "$params.path"
                                              }
                                          }
                                      }
                                  ),
                                  headers=self.auth)
        )
        self.assert200(s)
        self.assertEqual(r["_status"], "OK")
        r, s = self.parse_response(
            self.test_client.get('/api/v1/scripting/run_script_url/'
                                 'did:elastos:ij8krAVRJitZKJmcCufoLHQjq7Mef3ZjTN@appid/'
                                 f'script_upload_file?params={{"path":"{file_path}"}}')
        )
        transaction_id = r['upload_file']['transaction_id']
        r, s = self.parse_response(
            self.test_client.post(f'/api/v1/scripting/run_script_upload/{transaction_id}',
                                  data=f'{file_path} content 12345678')
        )
        self.assert200(s)
        self.assertEqual(r["_status"], "OK")

    def test03_download_file(self):
        logging.getLogger("HiveMongoScriptingTestCase").debug("\nRunning test03_download_file")
        file_path, script_name = 'scripting/test_01.txt', "script_download_file"
        file_content, executable_name = f'{file_path} content 12345678', 'download_file'
        r, s = self.parse_response(
            self.test_client.post('/api/v1/scripting/set_script',
                                  data=json.dumps(
                                      {
                                          "name": script_name,
                                          "allowAnonymousUser": True,
                                          "allowAnonymousApp": True,
                                          "executable": {
                                              "output": True,
                                              "name": executable_name,
                                              "type": "fileDownload",
                                              "body": {
                                                  "path": "$params.path"
                                              }
                                          }
                                      }
                                  ),
                                  headers=self.auth)
        )
        self.assert200(s)
        self.assertEqual(r["_status"], "OK")
        r, s = self.parse_response(
            self.test_client.post('/api/v1/scripting/run_script',
                                  data=json.dumps(
                                      {
                                          "name": script_name,
                                          "context": {
                                              "target_did": "did:elastos:ij8krAVRJitZKJmcCufoLHQjq7Mef3ZjTN",
                                              "target_app_did": "appid"
                                          },
                                          'params': {
                                              'path': file_path
                                          }
                                      }
                                  ))
        )
        self.assert200(s)
        self.assertEqual(r["_status"], "OK")
        transaction_id = r[executable_name]['transaction_id']
        r = self.test_client.post(f'/api/v1/scripting/run_script_download/{transaction_id}')
        self.assert200(r.status_code)
        self.assertEqual(r.get_data(as_text=True), file_content)

    def test04_file_properties(self):
        logging.getLogger("HiveMongoScriptingTestCase").debug("\nRunning test04_file_properties")
        file_path, script_name, executable_name = 'scripting/test_01.txt', "script_file_properties", 'file_properties'
        r, s = self.parse_response(
            self.test_client.post('/api/v1/scripting/set_script',
                                  data=json.dumps(
                                      {
                                          "name": script_name,
                                          "allowAnonymousUser": True,
                                          "allowAnonymousApp": True,
                                          "executable": {
                                              "output": True,
                                              "name": executable_name,
                                              "type": "fileProperties",
                                              "body": {
                                                  "path": "$params.path"
                                              }
                                          }
                                      }
                                  ),
                                  headers=self.auth)
        )
        self.assert200(s)
        self.assertEqual(r["_status"], "OK")
        r, s = self.parse_response(
            self.test_client.post('/api/v1/scripting/run_script',
                                  data=json.dumps(
                                      {
                                          "name": script_name,
                                          "context": {
                                              "target_did": "did:elastos:ij8krAVRJitZKJmcCufoLHQjq7Mef3ZjTN",
                                              "target_app_did": "appid"
                                          },
                                          'params': {
                                              'path': file_path
                                          }
                                      }
                                  ))
        )
        self.assert200(s)
        self.assertEqual(r["_status"], "OK")
        self.assertTrue(executable_name in r)

    def test05_file_hash(self):
        logging.getLogger("HiveMongoScriptingTestCase").debug("\nRunning test05_file_hash")
        file_path, script_name, executable_name = 'scripting/test_01.txt', "script_file_hash", 'file_hash'
        r, s = self.parse_response(
            self.test_client.post('/api/v1/scripting/set_script',
                                  data=json.dumps(
                                      {
                                          "name": script_name,
                                          "allowAnonymousUser": True,
                                          "allowAnonymousApp": True,
                                          "executable": {
                                              "output": True,
                                              "name": executable_name,
                                              "type": "fileHash",
                                              "body": {
                                                  "path": "$params.path"
                                              }
                                          }
                                      }
                                  ),
                                  headers=self.auth)
        )
        self.assert200(s)
        self.assertEqual(r["_status"], "OK")
        r, s = self.parse_response(
            self.test_client.post('/api/v1/scripting/run_script',
                                  data=json.dumps(
                                      {
                                          "name": script_name,
                                          "context": {
                                              "target_did": "did:elastos:ij8krAVRJitZKJmcCufoLHQjq7Mef3ZjTN",
                                              "target_app_did": "appid"
                                          },
                                          'params': {
                                              'path': file_path
                                          }
                                      }
                                  ))
        )
        self.assert200(s)
        self.assertEqual(r["_status"], "OK")
        self.assertTrue(executable_name in r)

    def test06_remove_all_test_files(self):
        self.do_remove_file('scripting/test_01.txt')
        self.do_remove_file('scripting/test_02.txt')

    def do_remove_file(self, path):
        r, s = self.parse_response(
            self.test_client.post('/api/v1/files/delete', data=json.dumps({"path": path}), headers=self.auth)
        )
        self.assert200(s)

    @unittest.skip("Just for manually test.")
    def test_8_1_run_script_with_url_exception(self):
        logging.getLogger('ScriptingTest').debug("Enter test_8_1_run_script_with_url_exception")
        r, s = self.parse_response(
            self.test_client.post('/api/v1/scripting/set_script', json={
                                      "name": "script_anonymous_access2",
                                      "allowAnonymousUser": True,
                                      "allowAnonymousApp": True,
                                      "executable": {
                                          "type": "find",
                                          "name": "get_all_groups",
                                          "body": {
                                              "collection": "groups2"
                                          }
                                      }
                                  }, headers=self.auth))
        self.assertEqual(s, 200)
        self.assertEqual(r["_status"], "OK")
        # run to get an error response.
        r, s = self.parse_response(
            self.test_client.get('/api/v1/scripting/run_script_url/'
                                 'did:elastos:ij8krAVRJitZKJmcCufoLHQjq7Mef3ZjTN@appid/'
                                 'script_anonymous_access2'))
        self.assertEqual(s, 400)
        self.assertEqual(r["_status"], "ERR")
        logging.getLogger('ScriptingTest').debug(f"test_8_1 error message: {r['_error']['message']}")


if __name__ == '__main__':
    unittest.main()
