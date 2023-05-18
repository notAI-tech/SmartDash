```python
from smartlogger import PipelineTimer

pipeline_timer = PipelineTimer(NAME, save_to_dir="./")

pipeline_timer.start(unique_id)
pipeline_timer.stage_success(unique_id, name="pre_processing")
pipeline_timer.stage_failed(unique_id, name="feature_extraction")
pipeline_timer.stage_success(unique_id, name="feature_extraction")
pipeline_timer.finished(unique_id)


from smartlogger import PipelineLogger

pipeline_logger = PipelineLogger(NAME, save_to_dir="./")

pipeline_logger.debug(u_id, "message_1", 6, {}, [], ...)
pipeline_logger.info(u_id, ....)
pipeline_logger.warning(u_id, ...)
pipeline_logger.exception(u_id, ....)
pipeline_logger.ml_inputs_outputs(u_id, INPUTS, OUTPUTS, MODEL_TYPE="")

```