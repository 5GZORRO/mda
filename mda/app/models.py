from .main import *

class Metric_Model(BaseModel):
  metric_name: str
  metric_type: str
  step: str
  aggregation_method: Optional[str] = None
  step_aggregation: Optional[str] = None

class Context_Model(BaseModel):
  resource_id: str
  network_slice_id: Optional[str] = None
  parent_id: Optional[str] = None

class Response_Metric_Model(BaseModel):
  metric_name: str
  metric_type: str
  step: str
  aggregation_method: Optional[str] = None
  step_aggregation: Optional[str] = None
  next_run_at: datetime.datetime
  next_aggregation: Optional[datetime.datetime] = None

class Config_Model(BaseModel):
  business_id: str
  topic: str
  monitoring_endpoint: str
  data_source_type: str
  tenant_id: str
  reference_id: str
  context_ids: List[Context_Model]
  metrics: List[Metric_Model]
  timestamp_start: Optional[datetime.datetime] = None
  timestamp_end: Optional[datetime.datetime] = None

class Update_Config_Model(BaseModel):
  timestamp_end: Optional[datetime.datetime] = None
  metrics: Optional[List[Metric_Model]] = None

class Response_Config_Model(BaseModel):
  id: uuid.UUID
  created_at: datetime.datetime
  updated_at: datetime.datetime
  business_id: str
  monitoring_endpoint: str
  topic: str
  resource_id: str
  network_id: str
  parent_id: str
  timestamp_start: datetime.datetime
  timestamp_end: Optional[datetime.datetime] = None	
  metrics: List[Response_Metric_Model]
  status: int
  tenant_id: str
  reference_id: str

class Response_Error_Model(BaseModel):
	status: str
	message: str
