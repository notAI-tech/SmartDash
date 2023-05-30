# SmartDash

### Use SmartLogger in your code

```python
from smartlogger import SmartLogger

logger = SmartLogger("examplePipelineName", save_to_dir="OPTIONAL_SAVE_DIR, defaults to ./")

stage = logger.Stage(unique_id, stage_name, tags=optional_list_of_tags)
# code block you want to log and time, eg: model inference/ db call/ pre/post processing code
# stage.debug()/ info()/ exception (logs exc info)/ error
# depending on whether it succeeded or not
stage.success()
stage.failed() 
```

```bash
# Process to continuously upload logs to dash
smartlogger --save_dir ./ --server_url "http://localhost:8080"
```


### Start SmartDash

```
# Start smartdash server
smartdash --dash --server_url "http://localhost:8080" --port 6788 --save_dir ./

# Start smartdash dashboard
smartdash --dash --server_url "http://localhost:8080" --port 6788 --save_dir ./
```
