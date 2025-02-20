# -*- coding: utf-8 -*-

"""
Testing file for the scripting module.
"""
import logging
import unittest
import json

from tests.utils.http_client import HttpClient
from tests import init_test
from tests.utils_v1 import test_common


@unittest.skip
class ScriptingTestCase(unittest.TestCase):
    collection_name = 'script_database'

    def __init__(self, method_name='runTest'):
        super().__init__(method_name)
        init_test()
        self.cli = HttpClient(f'/api/v2/vault')
        self.cli2 = HttpClient(f'/api/v2/vault', is_did2=True)
        self.file_name = 'scripting/test.txt'
        self.file_content = 'File Content: 12345678'
        # script owner's did and application did.
        self.did = self.cli.get_current_did()
        self.app_did = test_common.app_id

    @staticmethod
    def _subscribe():
        HttpClient(f'/api/v2').put('/subscription/vault')
        HttpClient(f'/api/v2', is_did2=True).put('/subscription/vault')

    @staticmethod
    def _create_collection():
        HttpClient(f'/api/v2/vault').put(f'/db/collections/{ScriptingTestCase.collection_name}')

    @staticmethod
    def _delete_collection():
        HttpClient(f'/api/v2/vault').delete(f'/db/{ScriptingTestCase.collection_name}')

    @classmethod
    def setUpClass(cls):
        cls._subscribe()
        cls._delete_collection()
        cls._create_collection()

    @classmethod
    def tearDownClass(cls):
        ScriptingTestCase._delete_collection()

    def __register_script(self, script_name, body):
        response = self.cli.put(f'/scripting/{script_name}', body)
        self.assertEqual(response.status_code, 200)
        return json.loads(response.text)

    def __call_script(self, script_name, body=None, is_raw=False):
        if body is None:
            body = dict()
        body['context'] = {
            'target_did': self.did,
            'target_app_did': self.app_did,
        }
        response = self.cli2.patch(f'/scripting-deprecated/{script_name}', body)
        self.assertEqual(response.status_code, 200)
        return response.text if is_raw else json.loads(response.text)

    def test01_register_script_insert(self):
        self.__register_script('database_insert', {
            "executable": {
                "output": True,
                "name": "database_insert",
                "type": "insert",
                "body": {
                    "collection": self.collection_name,
                    "document": {
                        "author": "$params.author",
                        "content": "$params.content"
                    },
                    "options": {
                        "ordered": True,
                        "bypass_document_validation": False
                    }
                }
            }
        })

    def test02_call_script_insert(self):
        self.__call_script('database_insert', {
            "params": {
                "author": "John",
                "content": "message"
            }
        })

    def test03_call_script_url_insert(self):
        response = self.cli2.get(f'/scripting-deprecated/database_insert/{self.did}@{self.app_did}'
                                 '/%7B%22author%22%3A%22John2%22%2C%22content%22%3A%22message2%22%7D')
        self.assertEqual(response.status_code, 200)

    def __call_script_for_transaction_id(self, script_name):
        response_body = self.__call_script(script_name, {
            "params": {
                "path": self.file_name
            }
        })
        self.assertEqual(type(response_body), dict)
        self.assertTrue(script_name in response_body)
        self.assertEqual(type(response_body[script_name]), dict)
        self.assertTrue('transaction_id' in response_body[script_name])
        return response_body[script_name]['transaction_id']

    def test04_find_with_default_output_find(self):
        name = 'database_find'
        col_filter = {'author': '$params.author'}
        body = self.__set_and_call_script(name, {'condition': {
                'name': 'verify_user_permission',
                'type': 'queryHasResults',
                'body': {
                    'collection': self.collection_name,
                    'filter': col_filter
                }
            }, 'executable': {
                'name': name,
                'type': 'find',
                'body': {
                    'collection': self.collection_name,
                    'filter': col_filter
                }
            }}, {'params': {'author': 'John'}})
        self.assertIsNotNone(body)

    def test04_find_with_anonymous(self):
        name = 'database_find2'
        col_filter = {'author': '$params.author'}
        script_body = {
            'condition': {
                'name': 'verify_user_permission',
                'type': 'queryHasResults',
                'body': {
                    'collection': self.collection_name,
                    'filter': col_filter
                }
            },
            'executable': {
                'name': name,
                'type': 'find',
                'body': {
                    'collection': self.collection_name,
                    'filter': col_filter
                }
            },
            "allowAnonymousUser": True,
            "allowAnonymousApp": True
        }
        run_body = {'params': {
            'author': 'John'
        }}
        body = self.__set_and_call_script(name, script_body, run_body)
        self.assertIsNotNone(body)

    def test05_update(self):
        name = 'database_update'
        col_filter = {'author': '$params.author'}
        body = self.__set_and_call_script(name, {'executable': {
            'name': name,
            'type': 'update',
            'output': True,
            'body': {
                'collection': self.collection_name,
                'filter': col_filter,
                'update': {
                    '$set': {
                        'author': '$params.author',
                        'content': '$params.content'
                    }
                }, 'options': {
                    'bypass_document_validation': False,
                    'upsert': True
                }
            }}}, {'params': {
                'author': 'John',
                'content': 'message2'
        }})
        self.assertIsNotNone(body)

    def test06_file_upload(self):
        name = 'file_upload'
        self.__register_script(name, {
            "executable": {
                "output": True,
                "name": name,
                "type": "fileUpload",
                "body": {
                    "path": "$params.path"
                }
            }
        })
        response = self.cli2.put(f'/scripting-deprecated/stream/{self.__call_script_for_transaction_id(name)}',
                                 self.file_content.encode(), is_json=False)
        self.assertEqual(response.status_code, 200)

    def test07_file_download(self):
        name = 'file_download'
        self.__register_script(name, {
            "executable": {
                "output": True,
                "name": name,
                "type": "fileDownload",
                "body": {
                    "path": "$params.path"
                }
            }
        })
        response = self.cli.get(f'/scripting-deprecated/stream/{self.__call_script_for_transaction_id(name)}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.text, self.file_content)

    def test08_file_properties_without_params(self):
        name = 'file_properties'
        body = self.__set_and_call_script(name, {'executable': {
            'name': name,
            'type': 'fileProperties',
            'output': True,
            'body': {
                'path': self.file_name
            }}})
        self.assertTrue(name in body)
        self.assertEqual(body[name]['size'], len(self.file_content))

    def test09_file_hash(self):
        name = 'file_hash'
        body = self.__set_and_call_script(name, {'executable': {
            'name': name,
            'type': 'fileHash',
            'output': True,
            'body': {
                'path': '$params.path'
            }}}, {'params': {'path': self.file_name}})
        self.assertIsNotNone(body)

    def test10_delete(self):
        name = 'database_delete'
        col_filter = {'author': '$params.author'}
        body = self.__set_and_call_script(name, {'executable': {
            'name': name,
            'type': 'delete',
            'output': True,
            'body': {
                'collection': self.collection_name,
                'filter': col_filter
            }}}, {'params': {'author': 'John'}})
        self.assertIsNotNone(body)

    def test11_delete_script(self):
        response = self.cli.delete('/scripting/database_insert')
        response = self.cli.delete('/scripting/database_find')
        response = self.cli.delete('/scripting/database_find2')
        response = self.cli.delete('/scripting/database_update')
        response = self.cli.delete('/scripting/database_delete')
        response = self.cli.delete('/scripting/file_upload')
        response = self.cli.delete('/scripting/file_download')
        response = self.cli.delete('/scripting/file_properties')
        response = self.cli.delete('/scripting/file_hash')
        self.assertEqual(response.status_code, 204)

    def __set_and_call_script(self, name, script_body, run_body=None):
        logging.debug(f'Register the script: {name}')
        self.__register_script(name, script_body)
        logging.debug(f'Call the script: {name}')
        return self.__call_script(name, run_body)


if __name__ == '__main__':
    unittest.main()
