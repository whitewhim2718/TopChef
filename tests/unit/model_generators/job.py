"""
Contains a generator for creating jobs
"""
from uuid import UUID
from datetime import datetime
from hypothesis.strategies import composite, uuids, text, sampled_from
from hypothesis.strategies import dictionaries, datetimes
from topchef.models import Job as JobInterface


class Job(JobInterface):
    """
    Provides an implementation of the ``JobInterface`` that works with
    randomly-generated data
    """
    def __init__(
            self,
            job_id: UUID,
            status: JobInterface.JobStatus,
            parameters: dict,
            results: dict,
            date_submitted: datetime,
            parameter_schema: dict,
            result_schema: dict
    ):
        self._job_id = job_id
        self._status = status
        self._parameters = parameters
        self._results = results
        self._date_submitted = date_submitted
        self._parameter_schema = parameter_schema
        self._result_schema = result_schema

    @property
    def id(self) -> UUID:
        return self._job_id

    @property
    def status(self) -> JobInterface.JobStatus:
        return self._status

    @status.setter
    def status(self, new_status: JobInterface.JobStatus) -> None:
        self._status = new_status

    @property
    def parameters(self) -> dict:
        return self._parameters

    @property
    def results(self) -> dict:
        return self._results

    @results.setter
    def results(self, new_results: dict) -> None:
        self._results = new_results

    @property
    def date_submitted(self) -> datetime:
        return self._date_submitted

    @property
    def parameter_schema(self) -> dict:
        return self._parameter_schema

    @property
    def result_schema(self) -> dict:
        return self._result_schema

    def __hash__(self) -> int:
        return hash((self.__class__.__name__, self.id))

    def __repr__(self) -> str:
        """

        :return: The code used to create this instance
        """
        return '%s(job_id=%s, status=%s, parameters=%s, results=%s, ' \
            'date_submitted=%s' % (
                self.__class__.__name__,
                self._job_id,
                self._status,
                self._parameters,
                self._results,
                self._date_submitted
            )


@composite
def jobs(
        draw,
        ids=uuids(),
        statuses=sampled_from(JobInterface.JobStatus),
        parameters=dictionaries(text(), text()),
        results=dictionaries(text(), text()),
        dates_submitted=datetimes(),
        registration_schemas=dictionaries(text(), text()),
        result_schemas=dictionaries(text(), text())
) -> JobInterface:
    return Job(
        draw(ids), draw(statuses), draw(parameters), draw(results),
        draw(dates_submitted),
        draw(registration_schemas),
        draw(result_schemas)
    )

