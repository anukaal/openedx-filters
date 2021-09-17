"""
Where filters log strategy is implemented.
"""
import logging

class FiltersLogStrategy:
    """
    Class that implements each log level for Open edX Filters.
    """
    DEBUG = "debug"
    PERFORMANCE = "performance"
    INFO = "info"

    def __init__(self, log_level):
        """
        Arguments:
            log_level (str): specifies which and how much information is logged.

        The available log levels are:
            - DEBUG
            - PERFORMANCE
            - INFO
        """
        self.log_level = log_level


    def set_level(self, log_level):
        """
        Sets log level for the class.

        Arguments:
            log_level (str): specifies which and how much information is logged.

        The available log levels are:
            - DEBUG
            - PERFORMANCE
            - INFO
        """
        self.log_level = log_level

    def is_enabled_for(self, log_level):
        """
        Check if the log level is enabled for the class.
        """
        return log_level == self.log_level

    def log(self):
        """
        Calls log method specified by log_level.
        """
        return {
            "debug": self.debug,
            "performance": self.performance,
            "info": self.info,
        }.get(self.log_level)()

    def debug(self):
        """
        Logs relevant information for debugging purposes using DEBUG method.
        """

    def performance(self):
        """
        Logs relevant information for debugging purposes using DEBUG method.
        """

    def error(self):
        """
        Logs relevant information for debugging purposes using DEBUG method.
        """

    def info(self):
        """
        Logs relevant information for debugging purposes using DEBUG method.
        """
