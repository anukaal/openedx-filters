"""
Tooling necessary to use Open edX Filters.
"""
from logging import getLogger

from django.conf import settings
from django.utils.module_loading import import_string

from openedx_filters.exceptions import OpenEdxFilterException
from openedx_filters.utils import FiltersLogStrategy

log = getLogger(__name__)


class OpenEdxPublicFilter:
    """
    Custom class used to create Open edX Filters.
    """

    filter_type = ""

    def __repr__(self):
        """
        Represent OpenEdxPublicFilter as a string.
        """
        return "<OpenEdxPublicFilter: {filter_type}>".format(filter_type=self.filter_type)

    @classmethod
    def get_functions_for_pipeline(cls, pipeline):
        """
        Get function objects from paths.

        Helper function that given a pipeline with functions paths gets
        the objects related to each path.

        Example usage:
            functions = get_functions_for_pipeline(
                [
                    '1st_path_to_function',
                    ...
                ]
            )
            >>> functions
            [
                <function 1st_function at 0x00000000000>,
                <function 2nd_function at 0x00000000001>,
                ...
            ]

        Arguments:
            pipeline (list): paths where functions are defined.

        Returns:
            function_list (list): function objects defined in pipeline.
        """
        function_list = []
        for function_path in pipeline:
            try:
                function = import_string(function_path)
                function_list.append(function)
            except ImportError:
                log.exception("Failed to import '%s'.", function_path)

        return function_list

    @classmethod
    def get_pipeline_configuration(cls):
        """
        Get pipeline configuration from filter settings.

        Helper function used to get the configuration needed to execute
        the Pipeline Runner. It will take from the hooks configuration
        the list of functions to execute and how to execute them.

        Example usage:
            pipeline_config = cls.get_pipeline_configuration()
            >>> pipeline_config
                (
                    [
                        'my_plugin.hooks.filters.test_function',
                        'my_plugin.hooks.filters.test_function_2nd',
                    ],
                )

        Returns:
            pipeline (list): paths where functions for the pipeline are
            defined.
            raise_exception (bool): defines whether exceptions are raised while
            executing the pipeline associated with a filter. It's determined by
            fail_silently configuration, True meaning it won't raise exceptions and
            False the opposite.
        """
        filter_config = cls.get_filter_config()

        if not filter_config:
            return [], False, "info"

        pipeline, raise_exception, log_level = [], False, "info"

        if isinstance(filter_config, dict):
            pipeline, raise_exception, log_level = (
                filter_config.get("pipeline", []),
                not filter_config.get("fail_silently", True),
                filter_config.get("log_level", "info"),
            )

        elif isinstance(filter_config, list):
            pipeline = filter_config

        elif isinstance(filter_config, str):
            pipeline.append(filter_config)

        return pipeline, raise_exception, log_level

    @classmethod
    def get_filter_config(cls):
        """
        Get filters configuration from settings.

        Helper function used to get configuration needed for using
        Hooks Extension Framework.

        Example usage:
                configuration = get_filter_config('trigger')
                >>> configuration
                {
                    'pipeline':
                        [
                            'my_plugin.hooks.filters.test_function',
                            'my_plugin.hooks.filters.test_function_2nd',
                        ],
                    'fail_silently': False,
                    'log_level': "debug"
                }

                Where:
                    - pipeline (list): paths where the functions to be executed by
                    the pipeline are defined.
                    - fail_silently (bool): determines whether the pipeline can
                    raise exceptions while executing. If its value is True then
                    exceptions (OpenEdxFilterException) are caught and the execution
                    continues, if False then exceptions are re-raised and the
                    execution fails.

        Arguments:
            filter_name (str): determines which configuration to use.

        Returns:
            filters configuration (dict): taken from Django settings
            containing filters configuration.
        """
        filters_config = getattr(settings, "OPEN_EDX_FILTERS_CONFIG", {})

        return filters_config.get(cls.filter_type, {})

    @classmethod
    def run_pipeline(cls, *args, **kwargs):
        """
        Execute filters in order.

        Given a list of functions paths, this function will execute
        them using the Accumulative Pipeline pattern defined in
        docs/decisions/0003-hooks-filter-tooling-pipeline.rst

        Example usage:
            filter_result = OpenEdxPublicFilter.run(
                user=user,
            )
            >>> filter_result
            {
                'result_test_1st_function': 1st_object,
                'result_test_2nd_function': 2nd_object,
            }

        Arguments:
            filter_name (str): determines which trigger we are listening to.
            It also specifies which filter configuration to use.

        Returns:
            accumulated_output (dict): accumulated outputs of the functions defined in pipeline.
            filter_result (obj): return object of one of the pipeline functions. This will
            be the returned by the pipeline if one of the functions returns
            an object different than Dict or None.

        Exceptions raised:
            OpenEdxFilterException: custom exception re-raised when a function raises
            an exception of this type and raise_exception is set to True. This
            behavior is common when using filters.

        This pipeline implementation was inspired by: Social auth core. For more
        information check their Github repository:
        https://github.com/python-social-auth/social-core
        """
        pipeline, raise_exception, log_level = cls.get_pipeline_configuration()
        log_strategy = FiltersLogStrategy(log_level=log_level)

        if not pipeline:
            return kwargs

        functions = cls.get_functions_for_pipeline(pipeline)

        accumulated_output = kwargs.copy()

        log_strategy.collect_pipeline_context(
            pipeline_steps=pipeline,
            raise_exception=raise_exception,
            initial_input=kwargs,
        )

        for function in functions:
            try:
                step_result = function(*args, **accumulated_output) or {}

                log_strategy.collect_step_context(
                    function.__name__,
                    accumulated_output=accumulated_output,
                    step_result=step_result,
                )

                if not isinstance(step_result, dict):
                    log.info(
                        "Pipeline stopped by '%s' for returning an object.",
                        function.__name__,
                    )
                    return step_result
                accumulated_output.update(step_result)
            except OpenEdxFilterException as exception:
                log_strategy.collect_step_context(
                    function.__name__,
                    accumulated_output=accumulated_output,
                    step_exception=exception,
                )
                log_strategy.log(
                    filter_type=cls.filter_type,
                    current_configuration=pipeline,
                )
                if raise_exception:
                    log.exception(
                        "Exception raised while running '%s':\n %s", function.__name__, exception,
                    )
                    raise
            except Exception as exception:  # pylint: disable=broad-except
                # We're catching this because we don't want the core to blow up
                # when a filter is broken. This exception will probably need some
                # sort of monitoring hooked up to it to make sure that these
                # errors don't go unseen.
                log.exception(
                    "Exception raised while running '%s': %s\n%s",
                    function.__name__,
                    exception,
                    "Continuing execution.",
                )
                log_strategy.collect_step_context(
                    function.__name__,
                    accumulated_output=accumulated_output,
                    step_exception=exception,
                )
                continue

        log_strategy.log(
            filter_type=cls.filter_type,
            current_configuration=pipeline,
        )

        return accumulated_output
