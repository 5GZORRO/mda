from .main import *

engine = create_engine('postgresql+psycopg2://' + POSTGRES_USER + ':' + POSTGRES_PASSWORD + '@' + POSTGRES_HOST + ':' + POSTGRES_PORT + '/' + POSTGRES_DB, pool_size=num_fetch_threads+num_fetch_threads_agg, convert_unicode=True)
# Create database if it does not exist.
if not database_exists(engine.url):
  create_database(engine.url)
db_session = scoped_session(sessionmaker(autocommit=False, autoflush=False, bind=engine))
Base = declarative_base()
Base.query = db_session.query_property()

class Config(Base):
  __tablename__ = 'config'
  _id = Column(postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, unique=True)
  created_at = Column(DateTime, default=datetime.datetime.now)
  updated_at = Column(DateTime, nullable=True)
  transaction_id  = Column(String(256), nullable=False)
  instance_id  = Column(String(256), nullable=True)
  product_id  = Column(String(256), nullable=True)
  kafka_topic = Column(String(256), nullable=False)
  monitoring_endpoint = Column(String(256), nullable=False)
  network_slice_id = Column(String(256), nullable=True)
  tenant_id = Column(String(256), nullable=False)
  resource_id = Column(String(256), nullable=False)
  parent_id = Column(String(256), nullable=True)
  timestamp_start = Column(DateTime, nullable=False)
  timestamp_end = Column(DateTime, nullable=True)
  status = Column(Integer, default=1)
  metrics = relationship("Metric", cascade="all, delete")

  def __init__(self, transaction_id, kafka_topic, network_slice_id, timestamp_start, timestamp_end, tenant_id, resource_id, parent_id, monitoring_endpoint, instance_id, product_id):
    self.transaction_id  = transaction_id
    self.instance_id = instance_id
    self.product_id = product_id
    self.kafka_topic = kafka_topic
    self.network_slice_id = network_slice_id
    self.timestamp_start = timestamp_start
    self.timestamp_end = timestamp_end
    self.tenant_id = tenant_id
    self.resource_id = resource_id
    self.parent_id = parent_id
    self.monitoring_endpoint = monitoring_endpoint
        
  def toString(self):
    return ({'id': self._id,
             'created_at': self.created_at,
             'updated_at': self.updated_at,
             'transaction_id': self.transaction_id,
             'instance_id': self.instance_id,
             'product_id': self.product_id,
             'topic': self.kafka_topic,
             'monitoring_endpoint': self.monitoring_endpoint,
             'timestamp_start': self.timestamp_start,
             'timestamp_end': self.timestamp_end,
             'metrics': [],
             'status': self.status,
             'tenant_id' : self.tenant_id,
             'context_ids': [
               {
                 'resource_id': self.resource_id,
                 'network_slice_id': self.network_slice_id,
                 'parent_id' : self.parent_id
               }
             ]})

class Metric(Base):
  __tablename__ = 'metric'
  _id = Column(postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, unique=True)
  config_id = Column(postgresql.UUID(as_uuid=True), ForeignKey('config._id'))
  metric_name = Column(String(256), nullable=False)
  metric_type = Column(String(256), nullable=False)
  aggregation_method = Column(String(256), nullable=True)
  step = Column(String(256), nullable=False)
  step_aggregation = Column(String(256), nullable=True)
  next_run_at = Column(DateTime, nullable=False)
  next_aggregation = Column(DateTime, nullable=True)
  status = Column(Integer, default=1)
  values = relationship("Value", cascade="all, delete")

  def __init__(self, metric_name, metric_type, aggregation_method, step, step_aggregation, config_id, next_run_at, next_aggregation):
    self.metric_name = metric_name
    self.metric_type = metric_type
    self.aggregation_method = aggregation_method
    self.step = step
    self.step_aggregation = step_aggregation
    self.config_id = config_id
    self.next_run_at = next_run_at
    self.next_aggregation = next_aggregation
        
  def toString(self):
    return ({'metric_name': self.metric_name,
             'metric_type': self.metric_type,
             'aggregation_method': self.aggregation_method,
             'step': self.step,
             'step_aggregation': self.step_aggregation,
             'next_run_at': self.next_run_at,
             'next_aggregation': self.next_aggregation})

class Value(Base):
  __tablename__ = 'value'
  timestamp = Column(DateTime, nullable=False, primary_key=True)
  metric_id = Column(postgresql.UUID(as_uuid=True), ForeignKey('metric._id'), primary_key=True)
  metric_value = Column(Float, nullable=False)

  def __init__(self, timestamp, metric_id, metric_value):
    self.timestamp = timestamp
    self.metric_id = metric_id
    self.metric_value = metric_value

# ----------------------------------------------------------------#
seconds_per_unit = {"s": 1, "m": 60, "h": 3600, "d": 86400, "w": 604800}

def convert_to_seconds(s):
  return int(s[:-1]) * seconds_per_unit[s[-1]]
 
def add_config(config: Config_Model, orchestrator, aggregator):

  try:
    row = Config(config.transaction_id, config.topic, config.context_ids[0].network_slice_id, config.timestamp_start, config.timestamp_end, config.tenant_id, config.context_ids[0].resource_id, config.context_ids[0].parent_id, config.monitoring_endpoint, config.instance_id, config.product_id)
    db_session.add(row)
    db_session.commit()
    response = row.toString()
    for metric in config.metrics:
      aggregation = None
      if metric.step_aggregation != None:
        sec_to_add = convert_to_seconds(metric.step_aggregation)
        aggregation = row.timestamp_start + relativedelta(seconds=sec_to_add)
      row_m = Metric(metric.metric_name, metric.metric_type, metric.aggregation_method, metric.step, metric.step_aggregation, row._id, row.timestamp_start, aggregation)
      db_session.add(row_m)
      db_session.commit()
      
      # Add to queue
      orchestrator.wait_queue.put((row_m.next_run_at, row.timestamp_start, row_m.step, row.timestamp_end, row_m._id, row_m.metric_name, row_m.metric_type, row_m.aggregation_method, row.transaction_id, row.kafka_topic, row.network_slice_id, row.tenant_id, row.resource_id, row_m.step_aggregation, row_m.next_aggregation, row.monitoring_endpoint, config.instance_id, config.product_id))
      if row_m.aggregation_method != None:
        aggregator.wait_queue_agg.put((row_m.next_aggregation, row.timestamp_start, row_m.step, row.timestamp_end, row_m._id, row_m.metric_name, row_m.metric_type, row_m.aggregation_method, row.transaction_id, row.kafka_topic, row.network_slice_id, row.tenant_id, row.resource_id, row_m.step_aggregation, row_m.next_aggregation, config.instance_id, config.product_id))
      
      response['metrics'].append(row_m.toString())
    return response
  except Exception as e:
    #print('database:add_config -> ' + str(e), flush=True)
    info_log(None, 'ERROR', 'Error in database:add_config: ' + str(e))
    return -1

def get_config(config_id):
  try:
    config = Config.query.filter_by(_id=config_id).first()
    if config == None:
      return 0
    response = config.toString()
    metrics = Metric.query.filter_by(config_id=config_id).all()
    [response['metrics'].append(metric.toString()) for metric in metrics]
    return response
  except Exception as e:
    #print('database:get_config -> ' + str(e), flush=True)
    info_log(None, 'ERROR', 'Error in database:get_config: ' + str(e))
    return -1

def get_configs():
  try:
    configs = Config.query.all()
    response = []
    for config in configs:
      add_metrics = config.toString()
      metrics = Metric.query.filter_by(config_id=config._id).all()
      [add_metrics['metrics'].append(metric.toString()) for metric in metrics]
      response.append(add_metrics)
    return response
  except Exception as e:
    #print('database:get_configs -> ' + str(e), flush=True)
    info_log(None, 'ERROR', 'Error in database:get_configs: ' + str(e))
    return -1

def delete_metric_queue(metric_id, orchestrator, aggregator):
  try:
    index = True
    while(index):
      index = False
      for i in range(len(orchestrator.wait_queue.queue)):
        if orchestrator.wait_queue.queue[i][4] == metric_id:
          del orchestrator.wait_queue.queue[i]
          index = True
          break
      for i in range(len(aggregator.wait_queue_agg.queue)):
        if aggregator.wait_queue_agg.queue[i][4] == metric_id:
          del aggregator.wait_queue_agg.queue[i]
          index = True
          break
      for i in range(len(orchestrator.metrics_queue.queue)):
        if orchestrator.metrics_queue.queue[i][4] == metric_id:
          del orchestrator.metrics_queue.queue[i]
          index = True
          break
      for i in range(len(aggregator.aggregation_queue.queue)):
        if aggregator.aggregation_queue.queue[i][4] == metric_id:
          del aggregator.aggregation_queue.queue[i]
          index = True
          break
    return
  except Exception as e:
    #print('database:delete_metric_queue -> ' + str(e), flush=True)
    info_log(metric_id, 'ERROR', 'Error in database:delete_metric_queue: ' + str(e))
    return -1

def update_config(config_id, config, orchestrator, aggregator):
  try:
    row = Config.query.filter_by(_id=config_id).first()
    if row == None:
      return 0
    if config.timestamp_end == None and config.metrics == None:
      return 1
      
    if config.timestamp_end != None and row.timestamp_end != None and config.timestamp_end <= row.timestamp_end:
      return 2
      
    now = datetime.datetime.now()
    row.updated_at = now
    # Update config
    if config.timestamp_end != None:
      row.timestamp_end = config.timestamp_end
    db_session.commit()
    response = row.toString()
    # Update metrics
    # Delete old metrics
    metrics = Metric.query.filter_by(config_id=config_id).all()
    for metric in metrics:
      delete_metric_queue(metric._id, orchestrator, aggregator)
      db_session.delete(metric)
    
    if config.metrics != None:
      #Create new metrics
      for metric in config.metrics:
        aggregation = None
        if metric.step_aggregation != None:
          sec_to_add = convert_to_seconds(metric.step_aggregation)
          aggregation = now + relativedelta(seconds=sec_to_add)
        row_m = Metric(metric.metric_name, metric.metric_type, metric.aggregation_method, metric.step, metric.step_aggregation, row._id, now, aggregation)
        db_session.add(row_m)
        db_session.commit()
        # Add to queue
        orchestrator.wait_queue.put((row_m.next_run_at, row.timestamp_start, row_m.step, row.timestamp_end, row_m._id, row_m.metric_name, row_m.metric_type, row_m.aggregation_method, row.transaction_id, row.kafka_topic, row.network_slice_id, row.tenant_id, row.resource_id, row_m.step_aggregation, row_m.next_aggregation, row.monitoring_endpoint, config.instance_id, config.product_id))
        if row_m.aggregation_method != None:
          aggregator.wait_queue_agg.put((row_m.next_aggregation, row.timestamp_start, row_m.step, row.timestamp_end, row_m._id, row_m.metric_name, row_m.metric_type, row_m.aggregation_method, row.transaction_id, row.kafka_topic, row.network_slice_id, row.tenant_id, row.resource_id, row_m.step_aggregation, row_m.next_aggregation, config.instance_id, config.product_id))
        response['metrics'].append(row_m.toString())
      return response
    return get_config(config_id)
  except Exception as e:
    #print('database:update_config -> ' + str(e), flush=True)
    info_log(None, 'ERROR', 'Error in database:update_config: ' + str(e))
    return -1

def update_next_run(metric_id, next):
  try:
    metric = Metric.query.filter_by(_id=metric_id).first()
    config = Config.query.filter_by(_id=metric.config_id).first()
    if config.timestamp_end != None and next > str(config.timestamp_end):
      metric.status = 0
      config.status = 0
      db_session.commit()
      return 0
    metric.next_run_at = next
    db_session.commit()
    return 1
  except Exception as e:
    #print('database:update_next_run -> ' + str(e), flush=True)
    info_log(metric_id, 'ERROR', 'Error in database:update_next_run: ' + str(e))
    return -1

def update_aggregation(metric_id, next):
  try:
    metric = Metric.query.filter_by(_id=metric_id).first()
    config = Config.query.filter_by(_id=metric.config_id).first()
    if config.timestamp_end != None and next > str(config.timestamp_end):
      metric.status = 0
      config.status = 0
      db_session.commit()
      return 0
    metric.next_aggregation = next
    db_session.commit()
    return 1
  except Exception as e:
    #print('database:update_aggregation -> ' + str(e), flush=True)
    info_log(metric_id, 'ERROR', 'Error in database:update_aggregation: ' + str(e))
    return -1

def enable_config(config_id, orchestrator, aggregator):
  try:
    config = Config.query.filter_by(_id=config_id).first()
    if config == None or (config.timestamp_end != None and config.timestamp_end < datetime.datetime.now()):
      return 0
    if config.status == 1:
      return 1
    config.status = 1
    now = datetime.datetime.now()
    config.updated_at = now
    add_metrics = config.toString()
    metrics = Metric.query.filter_by(config_id=config._id).all()
    for metric in metrics:
      metric.status = 1
      metric.next_run_at = now
      orchestrator.wait_queue.put((metric.next_run_at, config.timestamp_start, metric.step, config.timestamp_end, metric._id, metric.metric_name, metric.metric_type, metric.aggregation_method, config.transaction_id, config.kafka_topic, config.network_slice_id, config.tenant_id, config.resource_id, metric.step_aggregation, metric.next_aggregation, config.monitoring_endpoint, config.instance_id, config.product_id))
      if metric.aggregation_method != None:
        sec_to_add = convert_to_seconds(metric.step_aggregation)
        metric.next_aggregation = now + relativedelta(seconds=sec_to_add)
        aggregator.wait_queue_agg.put((metric.next_aggregation, config.timestamp_start, metric.step, config.timestamp_end, metric._id, metric.metric_name, metric.metric_type, metric.aggregation_method, config.transaction_id, config.kafka_topic, config.network_slice_id, config.tenant_id, config.resource_id, metric.step_aggregation, metric.next_aggregation, config.instance_id, config.product_id))
      add_metrics['metrics'].append(metric.toString())
      db_session.commit()
    return add_metrics
  except Exception as e:
    #print('database:enable_config -> ' + str(e), flush=True)
    info_log(None, 'ERROR', 'Error in database:enable_config: ' + str(e))
    return -1

def disable_config(config_id, orchestrator, aggregator):
  try:
    config = Config.query.filter_by(_id=config_id).first()
    if config == None:
      return 0
    if config.status == 0:
      return 1
    config.status = 0
    config.updated_at = datetime.datetime.now()
    add_metrics = config.toString()
    metrics = Metric.query.filter_by(config_id=config._id).all()
    for metric in metrics:
      metric.status = 0
      add_metrics['metrics'].append(metric.toString())
      delete_metric_queue(metric._id, orchestrator, aggregator)
      # Delete old data
      Value.query.filter_by(metric_id=metric._id).delete()
    db_session.commit()
    return add_metrics
  except Exception as e:
    #print('database:disable_config -> ' + str(e), flush=True)
    info_log(None, 'ERROR', 'Error in database:disable_config: ' + str(e))
    return -1

def delete_config(config_id, orchestrator, aggregator):
  try:
    config = Config.query.filter_by(_id=config_id).first()
    if config == None:
      return 0
    if config.status != 0 or config.updated_at + datetime.timedelta(minutes=1) > datetime.datetime.now():
      return 2
    
    metrics = Metric.query.filter_by(config_id=config._id).all()
    for metric in metrics:
      delete_metric_queue(metric._id, orchestrator, aggregator)
    
    db_session.delete(config)
    db_session.commit()
    return 1
  except Exception as e:
    #print('database:delete_config -> ' + str(e), flush=True)
    info_log(None, 'ERROR', 'Error in database:delete_config: ' + str(e))
    return -1

def load_database_metrics(orchestrator, aggregator):
  try:
    # Update old metrics and next executions
    now = datetime.datetime.now()
    db_session.execute("UPDATE config " \
                       "SET status = 0 " \
                       "WHERE status = 1 AND timestamp_end < '"+str(now)+"'; " \

                       "UPDATE metric " \
                       "SET next_run_at = '"+str(now)+"', " \
                           "next_aggregation = CASE WHEN aggregation_method is not null " \
                                                   "THEN '"+str(now)+"'::timestamp + step_aggregation::interval END " \
                       "FROM config c " \
                       "WHERE c.status = 1 AND next_run_at < '"+str(now)+"';");
    db_session.commit()
    # Get metrics
    result = db_session.execute("SELECT next_run_at, metric_name, metric_type, aggregation_method, step, transaction_id, instance_id, product_id, kafka_topic, network_slice_id, " \
                                       "tenant_id, resource_id, timestamp_start, timestamp_end, metric._id, step_aggregation, " \
                                       "next_aggregation, monitoring_endpoint " \
                                "FROM metric join config on metric.config_id = config._id " \
                                "WHERE metric.status = 1;")
    for row in result:
      orchestrator.wait_queue.put((row['next_run_at'], row['timestamp_start'], row['step'], row['timestamp_end'], row['_id'], row['metric_name'], row['metric_type'], row['aggregation_method'], row['transaction_id'], row['kafka_topic'], row['network_slice_id'], row['tenant_id'], row['resource_id'], row['step_aggregation'], row['next_aggregation'], row['monitoring_endpoint'], row['instance_id'], row['product_id']))
      if row['aggregation_method'] != None:
        aggregator.wait_queue_agg.put((row['next_aggregation'], row['timestamp_start'], row['step'], row['timestamp_end'], row['_id'], row['metric_name'], row['metric_type'], row['aggregation_method'], row['transaction_id'], row['kafka_topic'], row['network_slice_id'], row['tenant_id'], row['resource_id'], row['step_aggregation'], row['next_aggregation'], row['instance_id'], row['product_id']))
    return 1
  except Exception as e:
    #print('database:load_database_metrics -> ' + str(e), flush=True)
    info_log(None, 'ERROR', 'Error in database:load_database_metrics: ' + str(e))
    return -1

def insert_metric_value(metric_id, metric_value, timestamp):

  try:
    row = Value(timestamp, metric_id, metric_value)
    db_session.add(row)
    db_session.commit()
    return 1
  except Exception as e:
    #print('database:insert_metric_value -> ' + str(e), flush=True)
    info_log(metric_id, 'ERROR', 'Error in database:insert_metric_value: ' + str(e))
    return -1

def get_last_aggregation(metric_id, aggregation_method, bucket, step_aggregation):
  try:
    where_condition = "WHERE metric_id = '"+str(metric_id)+"' and timestamp < '"+str(bucket)+"'::timestamp and " \
                            "timestamp >= ('"+str(bucket)+"'::timestamp - interval '"+str(step_aggregation)+"');"
                            
    result = db_session.execute("SELECT "+aggregation_method+"(metric_value) " \
                                "FROM value " + where_condition).fetchone()
    
    # Delete old data
    db_session.execute("DELETE FROM value " + where_condition)
    db_session.commit()
    
    return result[0]
  except Exception as e:
    #print('database:get_last_aggregation -> ' + str(e), flush=True)
    info_log(metric_id, 'ERROR', 'Error in database:get_last_aggregation: ' + str(e))
    return -1

def create_index():
  db_session.execute("CREATE INDEX value_index ON value (timestamp ASC, metric_id);")
  db_session.commit()
  return

def close_connection():
  db_session.remove()
  return
  
def reload_connection():
  db_session.remove()
  db_session = scoped_session(sessionmaker(autocommit=False, autoflush=False, bind=engine))
  return

# ----------------------------------------------------------------#
# Reset db if env flag is True
if RESET_DB.lower() == 'true':
  try:
    try:
      db_session.commit()
      Base.metadata.drop_all(bind=engine)
    except Exception as e:
      print('database:reset_db -> ' + str(e), flush=True)
    Base.metadata.create_all(bind=engine)
    db_session.commit()
    create_index()
  except Exception as e:
    print('database:exception_reset_db -> ' + str(e), flush=True)
    sys.exit(0)

# Create db if not exists
try:
  resp1 = Config.query.first()
  resp2 = Metric.query.first()
  resp3 = Value.query.first()
  # Delete old data
  Value.query.delete()
except Exception as e:
  try:
    Base.metadata.create_all(bind=engine)
    db_session.commit()
    create_index()
  except Exception as e:
    print('database:create_db -> ' + str(e), flush=True)
    sys.exit(0)
