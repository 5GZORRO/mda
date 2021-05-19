from .main import *

@app.post("/settings", status_code=201, responses={201: {"model": Response_Config_Model,
														 "content": {"application/json": {
																	 "example": json_response_enable}}},
												   404: {"model": Response_Error_Model,
														 "content": {"application/json": {
																	 "example": {"status": "Error", "message": "Error message."}}}}})
async def set_param(config: Config_Model):

  for metric in config.metrics:
    if metric.aggregation_method != None and metric.aggregation_method.upper() not in agg_options:
      return JSONResponse(status_code=404, content={"status": "Error", "message": "Aggregation step options is "+str(agg_options)+"."})
    if metric.step_aggregation != None and metric.step_aggregation[-1] not in step_options and metric.step[-1] not in step_options:
      return JSONResponse(status_code=404, content={"status": "Error", "message": "Step and step aggregation options is "+str(step_options)+"."})
  if config.timestamp_start == None:
    config.timestamp_start = datetime.datetime.now()
  elif config.timestamp_start < datetime.datetime.now() - relativedelta(minutes=1):
    return JSONResponse(status_code=404, content={"status": "Error", "message": "Timestamp start need to be after current now."})
  if config.timestamp_end != None and config.timestamp_start > config.timestamp_end:
    return JSONResponse(status_code=404, content={"status": "Error", "message": "Timestamp start need to be after timestamp end."})
  
  # create public/private keys if not created 
  if config.tenant_id not in public_private_keys:
    public_key, private_key = rsa.newkeys(1024)
    public_private_keys[config.tenant_id] = {"public_key": public_key, "private_key": private_key}

  # Save config in database
  resp = add_config(config, orchestrator, aggregator)
  if resp == -1:
    return JSONResponse(status_code=404, content={"status": "Error", "message": "Error in create config in database."})
  orchestrator.update_queue_flag = True
  aggregator.update_queue_flag_agg = True
  info_log(200, f'Monitoring spec successfully created by operator {config.tenant_id}')
  return resp

@app.get("/settings/{config_id}", responses={200: {"model": Response_Config_Model,
												   "content": {"application/json": {
															   "example": json_response_enable}}},
											 404: {"model": Response_Error_Model,
												   "content": {"application/json": {
															   "example": {"status": "Error", "message": "Error message."}}}}})
async def get_config_id(config_id):
  # Get config by id
  if validate_uuid4(config_id) is False:
    return JSONResponse(status_code=404, content={"status": "Error", "message": "Config id invalid."})
  resp = get_config(config_id)
  if resp == 0:
    return JSONResponse(status_code=404, content={"status": "Error", "message": "Config id invalid."})
  if resp == -1:
    return JSONResponse(status_code=404, content={"status": "Error", "message": "Error in get config in database."})
  return resp

@app.get("/settings", responses={200: {"model": List[Response_Config_Model],
									   "content": {"application/json": {
												   "example": [json_response_enable]}}},
								 404: {"model": Response_Error_Model,
									   "content": {"application/json": {
												   "example": {"status": "Error", "message": "Error message."}}}}})
async def get_all_configs():
  # Get configs
  resp = get_configs()
  if resp == -1:
    return JSONResponse(status_code=404, content={"status": "Error", "message": "Error in get config in database."})
  return resp

@app.put("/settings/{config_id}", responses={200: {"model": Response_Config_Model,
												   "content": {"application/json": {
															   "example": json_response_enable}}},
											 404: {"model": Response_Error_Model,
												   "content": {"application/json": {
															   "example": {"status": "Error", "message": "Error message."}}}}})
async def update_config_id(config_id, config: Update_Config_Model):

  # Update config by id
  if validate_uuid4(config_id) is False:
    return JSONResponse(status_code=404, content={"status": "Error", "message": "Config id invalid."})
  resp = update_config(config_id, config, orchestrator, aggregator)
  if resp == 0:
    return JSONResponse(status_code=404, content={"status": "Error", "message": "Config id invalid."})
  if resp == 1:
    return JSONResponse(status_code=404, content={"status": "Error", "message": "Arguments invalid."})
  if resp == 2:
    return JSONResponse(status_code=404, content={"status": "Error", "message": "Timestamp end must be superior to the actual."})
  if resp == -1:
    return JSONResponse(status_code=404, content={"status": "Error", "message": "Error in update config in database."})
  orchestrator.update_queue_flag = True
  aggregator.update_queue_flag_agg = True
  info_log(200, f'Monitoring spec {config_id} successfully updated')
  return resp

@app.put("/settings/{config_id}/enable", responses={200: {"model": Response_Config_Model,
														  "content": {"application/json": {
																	  "example": json_response_enable}}},
													404: {"model": Response_Error_Model,
														  "content": {"application/json": {
																	  "example": {"status": "Error", "message": "Error message."}}}}})
async def enable_config_id(config_id):

  # Enable config by id
  if validate_uuid4(config_id) is False:
    return JSONResponse(status_code=404, content={"status": "Error", "message": "Config id invalid."})
  resp = enable_config(config_id, orchestrator, aggregator)
  if resp == 0:
    return JSONResponse(status_code=404, content={"status": "Error", "message": "Config id invalid."})
  if resp == 1:
    return JSONResponse(status_code=404, content={"status": "Error", "message": "Config already enabled."})
  if resp == -1:
    return JSONResponse(status_code=404, content={"status": "Error", "message": "Error in enable config in database."})
  orchestrator.update_queue_flag = True
  aggregator.update_queue_flag_agg = True
  info_log(200, f'Monitoring spec {config_id} successfully enabled')
  return resp

@app.put("/settings/{config_id}/disable", responses={200: {"model": Response_Config_Model,
														                               "content": {"application/json": {
                                                           "example": json_response_disable}}},
													 404: {"model": Response_Error_Model,
														   "content": {"application/json": {
																	   "example": {"status": "Error", "message": "Error message."}}}}})
async def disable_config_id(config_id):

  # Disable config by id
  if validate_uuid4(config_id) is False:
    return JSONResponse(status_code=404, content={"status": "Error", "message": "Config id invalid."})
  resp = disable_config(config_id)
  if resp == 0:
    return JSONResponse(status_code=404, content={"status": "Error", "message": "Config id invalid."})
  if resp == 1:
    return JSONResponse(status_code=404, content={"status": "Error", "message": "Config already disabled."})
  if resp == -1:
    return JSONResponse(status_code=404, content={"status": "Error", "message": "Error in disable config in database."})
  orchestrator.update_queue_flag = True
  aggregator.update_queue_flag_agg = True
  info_log(200, f'Monitoring spec {config_id} successfully disabled')
  return resp

@app.delete("/settings/{config_id}", status_code=HTTP_204_NO_CONTENT, responses={404: {"model": Response_Error_Model,
													  "content": {"application/json": {
																  "example": {"status": "Error", "message": "Error message."}}}}})
async def delete_config_id(config_id):

  # Get config by id
  if validate_uuid4(config_id) is False:
    return JSONResponse(status_code=404, content={"status": "Error", "message": "Config id invalid."})
  resp = delete_config(config_id)
  if resp == 0:
    return JSONResponse(status_code=404, content={"status": "Error", "message": "Config id invalid."})
  if resp == -1:
    return JSONResponse(status_code=404, content={"status": "Error", "message": "Error in delete config in database."})
  orchestrator.update_queue_flag = True
  aggregator.update_queue_flag_agg = True
  info_log(200, f'Monitoring spec {config_id} successfully deleted')

  return Response(status_code=HTTP_204_NO_CONTENT)
