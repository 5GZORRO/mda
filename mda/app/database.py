from .main import *

engine = create_engine('postgresql+psycopg2://' + POSTGRES_USER + ':' + POSTGRES_PW + '@' + POSTGRES_URL + '/' + POSTGRES_DB, convert_unicode=True)
connection = engine.raw_connection()
cur = connection.cursor(cursor_factory=psycopg2.extras.DictCursor)
# Create database if it does not exist.
if not database_exists(engine.url):
  create_database(engine.url)
else:
  engine.connect()
db_session = scoped_session(sessionmaker(autocommit=False, autoflush=False, bind=engine))
Base = declarative_base()
Base.query = db_session.query_property()

class Config(Base):
  __tablename__ = 'config'
  _id = Column(postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, unique=True)
  created_at = Column(DateTime, default=datetime.datetime.now)
  updated_at = Column(DateTime, nullable=True)
  business_id = Column(String(256), nullable=False)
  kafka_topic = Column(String(256), nullable=False)
  network_id = Column(String(256), nullable=False)
  tenant_id = Column(String(256), nullable=False)
  resource_id = Column(String(256), nullable=False)
  reference_id = Column(String(256), nullable=False)
  timestamp_start = Column(DateTime, nullable=False)
  timestamp_end = Column(DateTime, nullable=True)
  status = Column(Integer, default=1)
  metrics = relationship("Metric")

  def __init__(self, business_id, kafka_topic, network_id, timestamp_start, timestamp_end, tenant_id, resource_id, reference_id):
    self.business_id = business_id
    self.kafka_topic = kafka_topic
    self.network_id = network_id
    self.timestamp_start = timestamp_start
    self.timestamp_end = timestamp_end
    self.tenant_id = tenant_id
    self.resource_id = resource_id
    self.reference_id = reference_id
        
  def toString(self):
    return ({'id': self._id,
             'created_at': self.created_at,
             'updated_at': self.updated_at,
             'businessID': self.business_id,
             'topic': self.kafka_topic,
             'networkID': self.network_id,
             'timestampStart': self.timestamp_start,
             'timestampEnd': self.timestamp_end,
             'metrics': [],
             'status': self.status,
             'tenant_id' : self.tenant_id,
             'resource_id' : self.resource_id,
             'reference_id' : self.reference_id})

class Metric(Base):
  __tablename__ = 'metric'
  _id = Column(postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
  config_id = Column(postgresql.UUID(as_uuid=True), ForeignKey('config._id'))
  metric_name = Column(String(256), nullable=False)
  metric_type = Column(String(256), nullable=False)
  aggregation_method = Column(String(256), nullable=True)
  step = Column(String(256), nullable=False)
  next_run_at = Column(DateTime, primary_key=True, nullable=False)
  status = Column(Integer, default=1)

  def __init__(self, metric_name, metric_type, aggregation_method, step, config_id, next_run_at):
    self.metric_name = metric_name
    self.metric_type = metric_type
    self.aggregation_method = aggregation_method
    self.step = step
    self.config_id = config_id
    self.next_run_at = next_run_at
        
  def toString(self):
    return ({'metricName': self.metric_name,
             'metricType': self.metric_type,
             'aggregationMethod': self.aggregation_method,
             'step': self.step,
             'next_run_at': self.next_run_at})

# ----------------------------------------------------------------#
seconds_per_unit = {"s": 1, "m": 60, "h": 3600, "d": 86400, "w": 604800}

def convert_to_seconds(s):
  return int(s[:-1]) * seconds_per_unit[s[-1]]
 
def add_config(config: Config_Model):
  global wait_queue
  try:
    row = Config(config.businessID, config.topic, config.networkID, config.timestampStart, config.timestampEnd, config.tenantID, config.resourceID, config.referenceID)
    db_session.add(row)
    db_session.commit()
    response = row.toString()
    for metric in config.metrics:
      row_m = Metric(metric.metricName, metric.metricType, metric.aggregationMethod, metric.step, row._id, row.timestamp_start)
      db_session.add(row_m)
      db_session.commit()
      wait_queue.put((row_m.next_run_at, row.timestamp_start, row_m.step, row.timestamp_end, row_m._id, row_m.metric_name, row_m.metric_type, row_m.aggregation_method, row.business_id, row.kafka_topic, row.network_id, row.tenant_id, row.resource_id, row.reference_id))
      response['metrics'].append(row_m.toString())
    return response
  except Exception as e:
    print(e)
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
    print(e)
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
    print(e)
    return -1

def search_queue(metric_id):
  global wait_queue
  for i in range(len(wait_queue.queue)):
    if wait_queue.queue[i][4] == metric_id:
      return i
  return None

def update_config(config_id, config):
  global wait_queue
  try:
    row = Config.query.filter_by(_id=config_id).first()
    if row == None:
      return 0
    if config.timestampEnd != None and config.metrics != None:
      return 1
      
    if config.timestampEnd != None and config.timestampEnd <= row.timestamp_end:
      return 2
      
    row.updated_at = datetime.datetime.now()
    # Update config
    if config.timestampEnd != None:
      row.timestamp_end = config.timestampEnd
    db_session.commit()
    response = row.toString()
    # Update metrics
    # Delete old metrics
    metrics = Metric.query.filter_by(config_id=config_id).all()
    for metric in metrics:
      index_search = search_queue(metric._id)
      if index_search != None:
        del wait_queue.queue[index_search]
      db_session.delete(metric)
    
    if config.metrics != None:
      #Create new metrics
      for metric in config.metrics:
        row_m = Metric(metric.metricName, metric.metricType, metric.aggregationMethod, metric.step, config_id, datetime.datetime.now())
        db_session.add(row_m)
        db_session.commit()
        response['metrics'].append(row_m.toString())
        wait_queue.put((row_m.next_run_at, row.timestamp_start, row_m.step, row.timestamp_end, row_m._id, row_m.metric_name, row_m.metric_type, row_m.aggregation_method, row.business_id, row.kafka_topic, row.network_id, row.tenant_id, row.resource_id, row.reference_id))
      return response
    return get_config(config_id)
  except Exception as e:
    print(e)
    return -1

def update_next_run(metric_id, timestamp_end):
  global wait_queue
  try:
    metric = Metric.query.filter_by(_id=metric_id).first()
    config = Config.query.filter_by(_id=metric.config_id).first()
    sec_to_add = convert_to_seconds(metric.step)
    next = metric.next_run_at + relativedelta(seconds=sec_to_add)
    if timestamp_end != None and next > timestamp_end:
      metric.status = 0
      db_session.commit()
    else:
      metric.next_run_at = next
      db_session.commit()
      if metric.status == 1:
        wait_queue.put((metric.next_run_at, config.timestamp_start, metric.step, config.timestamp_end, metric._id, metric.metric_name, metric.metric_type, metric.aggregation_method, config.business_id, config.kafka_topic, config.network_id, config.tenant_id, config.resource_id, config.reference_id))
    return 1
  except Exception as e:
    #print(e)
    return -1


def enable_config(config_id):
  global wait_queue
  try:
    config = Config.query.filter_by(_id=config_id).first()
    if config == None or config.timestamp_end < datetime.datetime.now():
      return 0
    if config.status == 1:
      return 1
    config.status = 1
    config.updated_at = datetime.datetime.now()
    add_metrics = config.toString()
    metrics = Metric.query.filter_by(config_id=config._id).all()
    for metric in metrics:
      metric.status = 1
      db_session.commit()
      add_metrics['metrics'].append(metric.toString())
      index_search = search_queue(metric._id)
      if index_search == None:
        wait_queue.put((metric.next_run_at, config.timestamp_start, metric.step, config.timestamp_end, metric._id, metric.metric_name, metric.metric_type, metric.aggregation_method, config.business_id, config.kafka_topic, config.network_id, config.tenant_id, config.resource_id, config.reference_id))
    return add_metrics
  except Exception as e:
    print(e)
    return -1

def disable_config(config_id):
  global wait_queue
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
      index_search = search_queue(metric._id)
      if index_search != None:
	      del wait_queue.queue[index_search]
    db_session.commit()
    return add_metrics
  except Exception as e:
    print(e)
    return -1

def delete_config(config_id):
  global wait_queue
  try:
    config = Config.query.filter_by(_id=config_id).first()
    if config == None:
      return 0
    metrics = Metric.query.filter_by(config_id=config._id).all()

    for metric in metrics:
      index_search = search_queue(metric._id)
      if index_search != None:
        del wait_queue.queue[index_search]
      db_session.delete(metric)
      
    db_session.delete(config)
    db_session.commit()
    return 1
  except Exception as e:
    print(e)
    return -1

def load_database_metrics():
  global wait_queue
  try:
    connection = engine.connect()
    result = connection.execute("SELECT next_run_at, metric_name, metric_type, aggregation_method, step, business_id, kafka_topic, network_id, " \
                                       "tenant_id, resource_id, reference_id, timestamp_start, timestamp_end, metric._id " \
                                "FROM metric join config on metric.config_id = config._id " \
                                "WHERE metric.status = 1;")
    for row in result:
      wait_queue.put((row['next_run_at'], row['timestamp_start'], row['step'], row['timestamp_end'], row['_id'], row['metric_name'], row['metric_type'], row['aggregation_method'], row['business_id'], row['kafka_topic'], row['network_id'], row['tenant_id'], row['resource_id'], row['reference_id']))
    return 1
  except Exception as e:
    print(e)
    return -1

# ----------------------------------------------------------------#
# Create db if not exists
try:
  resp1 = Config.query.first()
  resp2 = Metric.query.first()
except Exception as e:
  try:
    Base.metadata.create_all(bind=engine)
    '''query_extension = "CREATE EXTENSION IF NOT EXISTS timescaledb;"
    query_index = "CREATE INDEX metrics_index ON metric (next_run_at ASC, _id);"
    query_create_metric_hypertable = "SELECT create_hypertable('metric', 'next_run_at');"
    cur.execute(query_extension)
    cur.execute(query_index)
    cur.execute(query_create_metric_hypertable)
    connection.commit()
    cur.close()'''
  except Exception as e:
    print(e)
    sys.exit(0)

# Reset db if env flag is True
if RESET_DB.lower() == 'true':
  try:
    try:
      db_session.commit()
      Base.metadata.drop_all(bind=engine)
    except Exception as e:
      print(e)
    Base.metadata.create_all(bind=engine)
    '''query_extension = "CREATE EXTENSION IF NOT EXISTS timescaledb;"
    query_index = "CREATE INDEX ON metric (next_run_at ASC);"
    query_create_metric_hypertable = "SELECT create_hypertable('metric', 'next_run_at');"
    cur.execute(query_extension)
    cur.execute(query_create_metric_hypertable)
    cur.execute(query_index)
    connection.commit()
    cur.close()'''
  except Exception as e:
    print(e)
    sys.exit(0)
