# Copyright 2014 Google Inc. All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import unittest2


class TestBatch(unittest2.TestCase):

    def _getTargetClass(self):
        from gcloud.datastore.batch import Batch

        return Batch

    def _makeOne(self, client):
        return self._getTargetClass()(client)

    def test_ctor(self):
        from gcloud.datastore._generated import datastore_pb2
        _DATASET = 'DATASET'
        _NAMESPACE = 'NAMESPACE'
        connection = _Connection()
        client = _Client(_DATASET, connection, _NAMESPACE)
        batch = self._makeOne(client)

        self.assertEqual(batch.dataset_id, _DATASET)
        self.assertEqual(batch.connection, connection)
        self.assertEqual(batch.namespace, _NAMESPACE)
        self.assertTrue(batch._id is None)
        self.assertTrue(isinstance(batch.mutations, datastore_pb2.Mutation))
        self.assertEqual(batch._partial_key_entities, [])

    def test_current(self):
        _DATASET = 'DATASET'
        connection = _Connection()
        client = _Client(_DATASET, connection)
        batch1 = self._makeOne(client)
        batch2 = self._makeOne(client)
        self.assertTrue(batch1.current() is None)
        self.assertTrue(batch2.current() is None)
        with batch1:
            self.assertTrue(batch1.current() is batch1)
            self.assertTrue(batch2.current() is batch1)
            with batch2:
                self.assertTrue(batch1.current() is batch2)
                self.assertTrue(batch2.current() is batch2)
            self.assertTrue(batch1.current() is batch1)
            self.assertTrue(batch2.current() is batch1)
        self.assertTrue(batch1.current() is None)
        self.assertTrue(batch2.current() is None)

    def test_put_entity_wo_key(self):
        _DATASET = 'DATASET'
        connection = _Connection()
        client = _Client(_DATASET, connection)
        batch = self._makeOne(client)

        self.assertRaises(ValueError, batch.put, _Entity())

    def test_put_entity_w_key_wrong_dataset_id(self):
        _DATASET = 'DATASET'
        connection = _Connection()
        client = _Client(_DATASET, connection)
        batch = self._makeOne(client)
        entity = _Entity()
        entity.key = _Key('OTHER')

        self.assertRaises(ValueError, batch.put, entity)

    def test_put_entity_w_partial_key(self):
        _DATASET = 'DATASET'
        _PROPERTIES = {'foo': 'bar'}
        connection = _Connection()
        client = _Client(_DATASET, connection)
        batch = self._makeOne(client)
        entity = _Entity(_PROPERTIES)
        key = entity.key = _Key(_DATASET)
        key._id = None

        batch.put(entity)

        mutated_entity = _mutated_pb(self, batch.mutations, 'insert_auto_id')
        self.assertEqual(mutated_entity.key, key._key)
        self.assertEqual(batch._partial_key_entities, [entity])

    def test_put_entity_w_completed_key(self):
        from gcloud.datastore.helpers import _property_tuples

        _DATASET = 'DATASET'
        _PROPERTIES = {
            'foo': 'bar',
            'baz': 'qux',
            'spam': [1, 2, 3],
            'frotz': [],  # will be ignored
            }
        connection = _Connection()
        client = _Client(_DATASET, connection)
        batch = self._makeOne(client)
        entity = _Entity(_PROPERTIES)
        entity.exclude_from_indexes = ('baz', 'spam')
        key = entity.key = _Key(_DATASET)

        batch.put(entity)

        mutated_entity = _mutated_pb(self, batch.mutations, 'upsert')
        self.assertEqual(mutated_entity.key, key._key)

        prop_dict = dict(_property_tuples(mutated_entity))
        self.assertEqual(len(prop_dict), 3)
        self.assertTrue(prop_dict['foo'].indexed)
        self.assertFalse(prop_dict['baz'].indexed)
        self.assertTrue(prop_dict['spam'].indexed)
        self.assertFalse(prop_dict['spam'].list_value[0].indexed)
        self.assertFalse(prop_dict['spam'].list_value[1].indexed)
        self.assertFalse(prop_dict['spam'].list_value[2].indexed)
        self.assertFalse('frotz' in prop_dict)

    def test_put_entity_w_completed_key_prefixed_dataset_id(self):
        from gcloud.datastore.helpers import _property_tuples

        _DATASET = 'DATASET'
        _PROPERTIES = {
            'foo': 'bar',
            'baz': 'qux',
            'spam': [1, 2, 3],
            'frotz': [],  # will be ignored
            }
        connection = _Connection()
        client = _Client(_DATASET, connection)
        batch = self._makeOne(client)
        entity = _Entity(_PROPERTIES)
        entity.exclude_from_indexes = ('baz', 'spam')
        key = entity.key = _Key('s~' + _DATASET)

        batch.put(entity)

        mutated_entity = _mutated_pb(self, batch.mutations, 'upsert')
        self.assertEqual(mutated_entity.key, key._key)

        prop_dict = dict(_property_tuples(mutated_entity))
        self.assertEqual(len(prop_dict), 3)
        self.assertTrue(prop_dict['foo'].indexed)
        self.assertFalse(prop_dict['baz'].indexed)
        self.assertTrue(prop_dict['spam'].indexed)
        self.assertFalse(prop_dict['spam'].list_value[0].indexed)
        self.assertFalse(prop_dict['spam'].list_value[1].indexed)
        self.assertFalse(prop_dict['spam'].list_value[2].indexed)
        self.assertFalse('frotz' in prop_dict)

    def test_delete_w_partial_key(self):
        _DATASET = 'DATASET'
        connection = _Connection()
        client = _Client(_DATASET, connection)
        batch = self._makeOne(client)
        key = _Key(_DATASET)
        key._id = None

        self.assertRaises(ValueError, batch.delete, key)

    def test_delete_w_key_wrong_dataset_id(self):
        _DATASET = 'DATASET'
        connection = _Connection()
        client = _Client(_DATASET, connection)
        batch = self._makeOne(client)
        key = _Key('OTHER')

        self.assertRaises(ValueError, batch.delete, key)

    def test_delete_w_completed_key(self):
        _DATASET = 'DATASET'
        connection = _Connection()
        client = _Client(_DATASET, connection)
        batch = self._makeOne(client)
        key = _Key(_DATASET)

        batch.delete(key)

        mutated_key = _mutated_pb(self, batch.mutations, 'delete')
        self.assertEqual(mutated_key, key._key)

    def test_delete_w_completed_key_w_prefixed_dataset_id(self):
        _DATASET = 'DATASET'
        connection = _Connection()
        client = _Client(_DATASET, connection)
        batch = self._makeOne(client)
        key = _Key('s~' + _DATASET)

        batch.delete(key)

        mutated_key = _mutated_pb(self, batch.mutations, 'delete')
        self.assertEqual(mutated_key, key._key)

    def test_commit(self):
        _DATASET = 'DATASET'
        connection = _Connection()
        client = _Client(_DATASET, connection)
        batch = self._makeOne(client)

        batch.commit()

        self.assertEqual(connection._committed,
                         [(_DATASET, batch._commit_request, None)])

    def test_commit_w_partial_key_entities(self):
        _DATASET = 'DATASET'
        _NEW_ID = 1234
        connection = _Connection(_NEW_ID)
        client = _Client(_DATASET, connection)
        batch = self._makeOne(client)
        entity = _Entity({})
        key = entity.key = _Key(_DATASET)
        key._id = None
        batch._partial_key_entities.append(entity)

        batch.commit()

        self.assertEqual(connection._committed,
                         [(_DATASET, batch._commit_request, None)])
        self.assertFalse(entity.key.is_partial)
        self.assertEqual(entity.key._id, _NEW_ID)

    def test_as_context_mgr_wo_error(self):
        _DATASET = 'DATASET'
        _PROPERTIES = {'foo': 'bar'}
        connection = _Connection()
        entity = _Entity(_PROPERTIES)
        key = entity.key = _Key(_DATASET)

        client = _Client(_DATASET, connection)
        self.assertEqual(list(client._batches), [])

        with self._makeOne(client) as batch:
            self.assertEqual(list(client._batches), [batch])
            batch.put(entity)

        self.assertEqual(list(client._batches), [])

        mutated_entity = _mutated_pb(self, batch.mutations, 'upsert')
        self.assertEqual(mutated_entity.key, key._key)
        self.assertEqual(connection._committed,
                         [(_DATASET, batch._commit_request, None)])

    def test_as_context_mgr_nested(self):
        _DATASET = 'DATASET'
        _PROPERTIES = {'foo': 'bar'}
        connection = _Connection()
        entity1 = _Entity(_PROPERTIES)
        key1 = entity1.key = _Key(_DATASET)
        entity2 = _Entity(_PROPERTIES)
        key2 = entity2.key = _Key(_DATASET)

        client = _Client(_DATASET, connection)
        self.assertEqual(list(client._batches), [])

        with self._makeOne(client) as batch1:
            self.assertEqual(list(client._batches), [batch1])
            batch1.put(entity1)
            with self._makeOne(client) as batch2:
                self.assertEqual(list(client._batches), [batch2, batch1])
                batch2.put(entity2)

            self.assertEqual(list(client._batches), [batch1])

        self.assertEqual(list(client._batches), [])

        mutated_entity1 = _mutated_pb(self, batch1.mutations, 'upsert')
        self.assertEqual(mutated_entity1.key, key1._key)

        mutated_entity2 = _mutated_pb(self, batch2.mutations, 'upsert')
        self.assertEqual(mutated_entity2.key, key2._key)

        self.assertEqual(connection._committed,
                         [(_DATASET, batch2._commit_request, None),
                          (_DATASET, batch1._commit_request, None)])

    def test_as_context_mgr_w_error(self):
        _DATASET = 'DATASET'
        _PROPERTIES = {'foo': 'bar'}
        connection = _Connection()
        entity = _Entity(_PROPERTIES)
        key = entity.key = _Key(_DATASET)

        client = _Client(_DATASET, connection)
        self.assertEqual(list(client._batches), [])

        try:
            with self._makeOne(client) as batch:
                self.assertEqual(list(client._batches), [batch])
                batch.put(entity)
                raise ValueError("testing")
        except ValueError:
            pass

        self.assertEqual(list(client._batches), [])

        mutated_entity = _mutated_pb(self, batch.mutations, 'upsert')
        self.assertEqual(mutated_entity.key, key._key)
        self.assertEqual(connection._committed, [])


class _PathElementPB(object):

    def __init__(self, id):
        self.id = id


class _KeyPB(object):

    def __init__(self, id):
        self.path_element = [_PathElementPB(id)]


class _Connection(object):
    _marker = object()
    _save_result = (False, None)

    def __init__(self, *new_keys):
        self._completed_keys = [_KeyPB(key) for key in new_keys]
        self._committed = []
        self._index_updates = 0

    def commit(self, dataset_id, commit_request, transaction_id):
        self._committed.append((dataset_id, commit_request, transaction_id))
        return self._index_updates, self._completed_keys


class _Entity(dict):
    key = None
    exclude_from_indexes = ()
    _meanings = {}


class _Key(object):
    _MARKER = object()
    _kind = 'KIND'
    _key = 'KEY'
    _path = None
    _id = 1234
    _stored = None

    def __init__(self, dataset_id):
        self.dataset_id = dataset_id

    @property
    def is_partial(self):
        return self._id is None

    def to_protobuf(self):
        from gcloud.datastore._generated import entity_pb2
        key = self._key = entity_pb2.Key()
        # Don't assign it, because it will just get ripped out
        # key.partition_id.dataset_id = self.dataset_id

        element = key.path_element.add()
        element.kind = self._kind
        if self._id is not None:
            element.id = self._id

        return key

    def completed_key(self, new_id):
        assert self.is_partial
        new_key = self.__class__(self.dataset_id)
        new_key._id = new_id
        return new_key


class _Client(object):

    def __init__(self, dataset_id, connection, namespace=None):
        self.dataset_id = dataset_id
        self.connection = connection
        self.namespace = namespace
        self._batches = []

    def _push_batch(self, batch):
        self._batches.insert(0, batch)

    def _pop_batch(self):
        return self._batches.pop(0)

    @property
    def current_batch(self):
        if self._batches:
            return self._batches[0]


def _assert_num_mutations(test_case, mutation_pb, num_mutations):
    total_mutations = (len(mutation_pb.upsert) +
                       len(mutation_pb.update) +
                       len(mutation_pb.insert) +
                       len(mutation_pb.insert_auto_id) +
                       len(mutation_pb.delete))
    test_case.assertEqual(total_mutations, num_mutations)


def _mutated_pb(test_case, mutation_pb, mutation_type):
    # Make sure there is only one mutation.
    _assert_num_mutations(test_case, mutation_pb, 1)

    mutated_pbs = getattr(mutation_pb, mutation_type, [])
    # Make sure we have exactly one protobuf.
    test_case.assertEqual(len(mutated_pbs), 1)
    return mutated_pbs[0]
