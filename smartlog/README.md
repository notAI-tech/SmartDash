```python
from smartlogger import SmartTimer

timer = SmartTimer(NAME, save_to_dir="./")

timer.start(unique_id)
timer.stage_success(unique_id, name="pre_processing")
timer.stage_failed(unique_id, name="feature_extraction")
timer.stage_success(unique_id, name="feature_extraction")
timer.finished(unique_id)


from smartlogger import SmartLogger

logger = SmartLogger(NAME, save_to_dir="./")

logger.debug(u_id, "message_1", 6, {}, [], ...)
logger.info(u_id, ....)
logger.warning(u_id, ...)
logger.exception(u_id, ....)
logger.ml_inputs_outputs(u_id, INPUTS, OUTPUTS, MODEL_TYPE="")

```