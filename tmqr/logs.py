import logging
import os
from datetime import datetime


class TMQRLogger(logging.Logger):
    def __init__(self, global_log_name):
        super().__init__(global_log_name)

        self.logger_name = 'tmqr_framework2'
        self.logger_class = 'framework'
        self.logger = self

        #
        # Global settings
        #
        self.log_level = logging.DEBUG
        self.setup(self.logger_class, self.logger_name)

    def setup(self, logger_class, name, to_file=False, log_level=None):
        self.logger_class = logger_class

        if to_file:
            self.log_dir = os.path.join(os.path.dirname(os.path.realpath(__file__)), '..', 'logs')
            if not os.path.exists(self.log_dir):
                os.mkdir(self.log_dir)

            if not os.path.exists(os.path.join(self.log_dir, f'{datetime.now():%Y-%m-%d}')):
                os.mkdir(os.path.join(self.log_dir, f'{datetime.now():%Y-%m-%d}'))

            if not os.path.exists(os.path.join(self.log_dir, f'{datetime.now():%Y-%m-%d}', self.logger_class)):
                os.mkdir(os.path.join(self.log_dir, f'{datetime.now():%Y-%m-%d}', self.logger_class))

        for hdlr in self.logger.handlers[:]:
            try:
                # Closing file descriptors for logs
                if isinstance(hdlr, logging.FileHandler):
                    hdlr.stream.close()
            except:
                pass

            self.logger.removeHandler(hdlr)

        #formatter = logging.Formatter(fmt=f'%(asctime)s - %(levelname)s - %(message)s')
        formatter = logging.Formatter(fmt=f'%(asctime)s [%(filename)s:%(lineno)s - %(funcName)20s() ] %(levelname)s - %(message)s')

        handler_console = logging.StreamHandler()
        handler_console.setFormatter(formatter)

        if to_file:
            handler_file = logging.FileHandler(os.path.join(self.log_dir,
                                                            f'{datetime.now():%Y-%m-%d}',
                                                            self.logger_class,
                                                            f'{name}.log'))
            handler_file.setFormatter(formatter)
            self.logger.addHandler(handler_file)

        if log_level is None:
            self.logger.setLevel(self.log_level)
        else:
            self.logger.setLevel(log_level)
        self.logger.addHandler(handler_console)
"""
    def exception(self, msg):
        self.logger.exception(msg)
    
    def error(self, msg):
        self.logger.error(msg)
    
    def warn(self, msg):
        self.logger.warning(msg)
    
    def waring(self, msg):
        self.warn(msg)
    
    def info(self, msg):
        self.logger.info(msg)
        
    def debug(self, msg):
        self.logger.debug(msg)
"""

log = TMQRLogger('tmqr_framework2')