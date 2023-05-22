```python
from smartlogger import SmartTimer

timer = SmartTimer(NAME, save_to_dir="./")

timer.start(unique_id)

timer.start(unique_id, stage="pre_processing")
# code
timer.finished(unique_id, stage="pre_processing")
# if failed
timer.failed(unique_id, stage="pre_processing")


timer.start(unique_id, stage="feature_extraction")
# code
timer.finished(unique_id, stage="feature_extraction")
# if failed
timer.failed(unique_id, stage="feature_extraction")

timer.finished(unique_id)

```


```
from smartlogger import SmartLogger

# Initialize a SmartLogger instance
logger = SmartLogger("my_application", save_to_dir="./logs")

# Use the SmartLogger instance to log messages with different log levels

# Log a debug message without stage
logger.debug("id_1", "This is a debug message.")

# Log a debug message with stage
logger.debug("id_2", "This is a debug message with stage.", stage="data_processing")

# Log an info message with stage
logger.info("id_4", "This is an info message with stage.", stage="model_training")

# Log an exception message without stage
try:
    raise ValueError("This is a ValueError.")
except ValueError as e:
    logger.exception("id_7", "An exception occurred:", e)
```
