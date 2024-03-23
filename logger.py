import logging
import sys

class ColoredFormatter(logging.Formatter):
    blue = "\x1b[34;1m"
    cyan = "\x1b[36;1m"
    green = "\x1b[32;1m"
    yellow = "\x1b[33;1m"
    red = "\x1b[31;1m"
    bold_red = "\x1b[31;1m"
    reset = "\x1b[0m"
    format = "%(asctime)s - %(filename)s - %(levelname)s - %(message)s"

    FORMATS = {
        logging.DEBUG: blue + format + reset,  # 将 DEBUG 级别的日志设置为蓝色
        logging.INFO: cyan + format + reset,   # 将 INFO 级别的日志设置为青色
        logging.WARNING: yellow + format + reset,
        logging.ERROR: red + format + reset,
        logging.CRITICAL: bold_red + format + reset
    }

    def format(self, record):
        log_fmt = self.FORMATS.get(record.levelno)
        formatter = logging.Formatter(log_fmt, "%Y-%m-%d %H:%M:%S")
        return formatter.format(record)

# 创建一个日志记录器
logger = logging.getLogger('MyLogger')
logger.setLevel(logging.DEBUG)

# 创建一个用于输出到控制台的处理器
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(logging.DEBUG)

# 设置日志格式
console_handler.setFormatter(ColoredFormatter())

# 将处理器添加到日志记录器
logger.addHandler(console_handler)

# 使用方式
if __name__ == "__main__":
    logger.debug("这是一条 DEBUG 级别的信息")
    logger.info("这是一条 INFO 级别的信息")
    logger.warning("这是一条 WARNING 级别的信息")
    logger.error("这是一条 ERROR 级别的信息")
    logger.critical("这是一条 CRITICAL 级别的信息")
