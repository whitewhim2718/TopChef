"""
Contains unit tests for :mod:`topchef.api_server`
"""
import json
import os
from contextlib import contextmanager
from uuid import UUID

import mock
import pytest
from flask import jsonify
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import topchef.api_server as server
from topchef.api_server import app
from topchef.config import config
from topchef.database.schema import METADATA

try:
    DATABASE_URI = os.environ['DATABASE_URI']
except KeyError:
    DATABASE_URI = 'sqlite://'

JOB_REGISTRATION_SCHEMA = {
    "name": "TestService",
    "description": "Some test data",
    "job_registration_schema": {
        "type": "object",
        "properties": {
            "value": {
                "type": "integer"
            }
        }
    }
}

VALID_JOB_SCHEMA = {'parameters': {'value': 1}}


@pytest.yield_fixture
def schema_directory():

    if not os.path.isdir(config.SCHEMA_DIRECTORY):
        os.mkdir(config.SCHEMA_DIRECTORY)

    yield

    if os.path.isdir(config.SCHEMA_DIRECTORY):
        if not os.listdir(config.SCHEMA_DIRECTORY):
            os.removedirs(config.SCHEMA_DIRECTORY)


@pytest.fixture()
def database(schema_directory):
    engine = create_engine(DATABASE_URI)

    config._engine = engine

    METADATA.create_all(bind=engine)
    server.SESSION_FACTORY = sessionmaker(bind=engine)


@contextmanager
def app_client(endpoint):
    app_client = app.test_client()
    request_context = app.test_request_context()

    request_context.push()

    yield app_client

    request_context.pop()


@pytest.fixture
def posted_service(database):
    endpoint = '/services'

    with app_client(endpoint) as client:
        response = client.post(
            endpoint, headers={'Content-Type': 'application/json'},
            data=json.dumps(JOB_REGISTRATION_SCHEMA)
        )

        assert response.status_code == 201

        data = json.loads(response.data.decode('utf-8'))

        service_id = UUID(data['data']['service_details']['id'])

    return service_id


@pytest.fixture
def posted_job(database, posted_service):
    endpoint = '/services/%s/jobs' % str(posted_service)

    with app_client(endpoint) as client:
        response = client.post(
            endpoint, headers={'Content-Type': 'application/json'},
            data=json.dumps(VALID_JOB_SCHEMA)
        )

        assert response.status_code == 201

        data = json.loads(response.data.decode('utf-8'))
        
        job_id = UUID(data['data']['job_details']['id'])

    return job_id


class TestGetServiceJobs(object):
    def test_get_jobs(self, posted_service, posted_job):
        endpoint = 'services/%s/jobs' % str(posted_service)

        with app_client(endpoint) as client:
            response = client.get(
                endpoint, headers={'Content-Type': 'application/json'}
            )

        assert response.status_code == 200

    def test_get_job(self, posted_service, posted_job):
        endpoint = 'jobs/%s' % (str(posted_job))

        with app_client(endpoint) as client:
            response = client.get(
                endpoint, headers={'Content-Type': 'application/json'}
            )
        
        assert response.status_code == 200

    def test_get_job_404(self, posted_service, posted_job):
        job_id = 'foo'
        assert job_id != str(posted_job)

        endpoint = 'jobs/%s' % (job_id)

        with app_client(endpoint) as client:
            response = client.get(
                endpoint, headers={'Content-Type': 'application/json'}
            )

        assert response.status_code == 404


class TestGetServiceQueue(object):
    
    @mock.patch('topchef.api_server.UUID', side_effect=ValueError(
        'Kaboom'))
    def test_get_service_queue_error(self, mock_error):
        service_uuid = 'd753ddf0-7053-11e6-b1ce-843a4b768af4'
        endpoint = '/services/%s/queue' % (service_uuid)

        with app_client(endpoint) as client:
            with mock.patch('topchef.api_server.jsonify',
                            return_value=jsonify({})) as mock_jsonify:
                response = client.get(
                    endpoint, headers={'Content-Type': 'application/json'}
                )

        assert response.status_code == 404
        assert mock_jsonify.call_args == mock.call(
            {'errors': 'Could not parse job_id=%s as a UUID' % service_uuid}
        )

    def test_get_service_no_job(self, posted_service):
        """

        Tests that if there isn't a job available, then the returned status
        code is 204: NO CONTENT

        :param posted_service: The fixture for a service with no jobs
        """
        endpoint = '/services/%s/queue' % str(posted_service)
        with app_client(endpoint) as client:
            response = client.get(endpoint)

        assert response.status_code == 204

    def test_get_service_with_job(self, posted_service, posted_job):
        endpoint = '/services/%s/queue' % str(posted_service)

        with app_client(endpoint) as client:
            response = client.get(endpoint)

        assert response.status_code == 200

    @mock.patch('sqlalchemy.orm.Query.first', return_value=None)
    def test_no_service(self, mock_first, posted_service):
        endpoint = '/services/%s/queue' % str(posted_service)

        with app_client(endpoint) as client:
            with mock.patch('topchef.api_server.jsonify',
                            return_value=jsonify({})) as mock_jsonify:
                response = client.get(endpoint)

        assert response.status_code == 404
        assert mock_jsonify.call_args == mock.call(
            {'errors': 'Could not find service with id %s' % str(posted_service)
            }
        )


class TestGetJobQueue(object):
    def test_get_queue(self, posted_service, posted_job):
        endpoint = 'services/%s/queue' % str(posted_service)

        with app_client(endpoint) as client:
            response = client.get(
                endpoint, headers={'Content-Type': 'application/json'}
            )

        assert response.status_code == 200
        assert json.loads(response.data.decode('utf-8'))

    def test_get_empty_queue(self, posted_service):
        endpoint = 'services/%s/queue' % str(posted_service)

        with app_client(endpoint) as client:
            response = client.get(
                endpoint, headers={'Content-Type': 'application/json'}
            )

        assert response.status_code == 204


class TestPutJob(object):
    @staticmethod
    def get_job_details(endpoint):
        with app_client(endpoint) as client:
            response = client.get(
                endpoint, headers={'Content-Type': 'application/json'}
            )
        assert response.status_code == 200

        job_details = json.loads(response.data.decode('utf-8'))['data']

        return job_details

    def test_happy_path(self, posted_job):
        endpoint = '/jobs/%s' % str(posted_job)

        job_details = self.get_job_details(endpoint)

        job_details['status'] = "WORKING"

        with app_client(endpoint) as client:
            response = client.put(
                endpoint, headers={'Content-Type': 'application/json'},
                data=json.dumps(job_details))

        assert response.status_code == 200

    def test_no_uuid(self, posted_job):
        endpoint = '/jobs/foo'

        with app_client(endpoint) as client:
            response = client.put(
                endpoint, headers={'Content-Type': 'application/json'},
                data=json.dumps({'irrelevant': 'data'})
            )
        assert response.status_code == 404

    @mock.patch('sqlalchemy.orm.Query.first', return_value=None)
    def test_no_job(self, mock_first, posted_job):
        endpoint = '/jobs/%s' % str(posted_job)

        with app_client(endpoint) as client:
            response = client.put(endpoint,
                headers={'Content-Type': 'application/json'},
                data=json.dumps({'irrelevant': 'data'})
            )

        assert response.status_code == 404


@pytest.fixture
def next_job(database, posted_job, posted_service):
    endpoint = '/services/%s/jobs' % str(posted_service)

    with app_client(endpoint) as client:
        response = client.post(
            endpoint, headers={'Content-Type': 'application/json'},
            data=json.dumps(VALID_JOB_SCHEMA)
        )

        assert response.status_code == 201

    data = json.loads(response.data.decode('utf-8'))

    job_id = UUID(data['data']['job_details']['id'])

    return job_id

class TestNextJob(object):
    
    def test_next_job_204(self, posted_job):
        
        assert isinstance(posted_job, UUID)
        
        endpoint = '/jobs/%s/next' % str(posted_job)

        with app_client(endpoint) as client:
            response = client.get(endpoint,
                headers={'Content-Type': 'application/json'}
            )

        assert response.status_code == 204
    
    def test_next_job_redirect(self, next_job, posted_job):
        endpoint = '/jobs/%s/next' % str(posted_job)
        
        with app_client(endpoint) as client:
            response = client.get(endpoint,
                headers={'Content-Type': 'application/json'}
            )

        assert response.status_code == 302

