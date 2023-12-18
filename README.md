# SmartDash

### Use SmartLogger in your code

```python
from smartlogger import SmartLogger

logger = SmartLogger("examplePipelineName", dir="OPTIONAL_SAVE_DIR, defaults to ./", log_to_console=False (defaults to False))

stage = logger.Stage(unique_id, stage_name, tags=optional_list_of_tags)
# code block you want to log and time, eg: model inference/ db call/ pre/post processing code
# stage.debug()/ info()/ exception (logs exc info)/ error
# depending on whether it succeeded or not
stage.success()
stage.failed() 

stage.key_value(string_key, any_value, name=None default None, tags=[] default [])
```

```bash
# Process to continuously upload logs to dash
smartlogger --save_dir ./ --server_url "http://localhost:8080"
```


### Start SmartDash

```
# Start smartdash server
smartdash --server --port 6789 --save_dir ./

# Start smartdash dashboard
smartdash --dash --server_url "http://localhost:6789" --port 6788 --save_dir ./

# access the dashboard at localhost:6788
```
