from .main import *

engine = create_engine('postgresql+psycopg2://' + POSTGRES_USER + ':' + POSTGRES_PW + '@' + POSTGRES_URL + '/' + POSTGRES_DB, convert_unicode=True)
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
    business_id = Column(Integer, nullable=False)
    kafka_topic = Column(String(250), nullable=False)
    network_id = Column(Integer, nullable=False)
    timestamp_start = Column(DateTime, nullable=False)
    timestamp_end = Column(DateTime, nullable=True)
    status = Column(Integer, default=1)
    metrics = relationship("Metric")

    def __init__(self, business_id, kafka_topic, network_id, timestamp_start, timestamp_end):
        self.business_id = business_id
        self.kafka_topic = kafka_topic
        self.network_id = network_id
        self.timestamp_start = timestamp_start
        self.timestamp_end = timestamp_end
        
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
                 'status': self.status})

class Metric(Base):
    __tablename__ = 'metric'
    _id = Column(postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, unique=True)
    config_id = Column(postgresql.UUID(as_uuid=True), ForeignKey('config._id'))
    metric_name = Column(String(250), nullable=False)
    metric_type = Column(String(250), nullable=False)
    aggregation_method = Column(String(250), nullable=True)
    timestamp_step = Column(String(10), nullable=False)

    def __init__(self, metric_name, metric_type, aggregation_method, timestamp_step, config_id):
        self.metric_name = metric_name
        self.metric_type = metric_type
        self.aggregation_method = aggregation_method
        self.timestamp_step = timestamp_step
        self.config_id = config_id
        
    def toString(self):
        return ({'id': self._id,
                 'metricName': self.metric_name,
                 'metricType': self.metric_type,
                 'aggregationMethod': self.aggregation_method,
                 'timestampStep': self.timestamp_step})

# ----------------------------------------------------------------#
def add_config(config: Config_Model):
    try:
        row = Config(config.businessID, config.topic, config.networkID, config.timestampStart, config.timestampEnd)
        db_session.add(row)
        db_session.commit()
        response = row.toString()
        for metric in config.metrics:
          row_m = Metric(metric.metricName, metric.metricType, metric.aggregationMethod, metric.timestampStep, row._id)
          db_session.add(row_m)
          db_session.commit()
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
          for metric in add_metrics['metrics']:
            del metric['id']
          response.append(add_metrics)
        return response
    except Exception as e:
        print(e)
        return -1

def update_config(config_id, config):
    try:
        row = Config.query.filter_by(_id=config_id).first()
        if row == None:
          return 0
        if config.timestampStart != None or config.timestampEnd != None or config.metrics != None:
          row.updated_at = datetime.datetime.now()
        else:
          return 1
        if config.timestampStart != None:
          row.timestamp_start = config.timestampStart
        if config.timestampEnd != None:
          row.timestamp_end = config.timestampEnd
        db_session.commit()
        response = row.toString()
        if config.metrics != None:
          # Delete old metrics
          metrics = Metric.query.filter_by(config_id=config_id).all()
          [db_session.delete(metric) for metric in metrics]
          #Create new metrics
          for metric in config.metrics:
            row_m = Metric(metric.metricName, metric.metricType, metric.aggregationMethod, metric.timestampStep, row._id)
            db_session.add(row_m)
            db_session.commit()
            response['metrics'].append(row_m.toString())
        else:
          metrics = Metric.query.filter_by(config_id=config_id).all()
          [response['metrics'].append(metric.toString()) for metric in metrics]
        return response
    except Exception as e:
        print(e)
        return -1

def enable_config(config_id):
    try:
        config = Config.query.filter_by(_id=config_id).first()
        if config == None:
          return 0
        if config.status == 1:
          return 1
        config.status = 1
        config.updated_at = datetime.datetime.now()
        add_metrics = config.toString()
        metrics = Metric.query.filter_by(config_id=config._id).all()
        [add_metrics['metrics'].append(metric.toString()) for metric in metrics]
        db_session.commit()
        return add_metrics
    except Exception as e:
        print(e)
        return -1

def disable_config(config_id):
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
        [add_metrics['metrics'].append(metric.toString()) for metric in metrics]
        db_session.commit()
        return add_metrics
    except Exception as e:
        print(e)
        return -1

def delete_config(config_id):
    try:
        config = Config.query.filter_by(_id=config_id).first()
        if config == None:
          return 0
        metrics = Metric.query.filter_by(config_id=config._id).all()
        [db_session.delete(metric) for metric in metrics]
        db_session.delete(config)
        db_session.commit()
        return 1
    except Exception as e:
        print(e)
        return -1
# ----------------------------------------------------------------#
#Create db if not exists
#try:
#    resp1 = Config.query.first()
#    resp2 = Metric.query.first()
#except Exception as e:
try:
    try:
      Base.metadata.drop_all(bind=engine)
    except Exception as e:
      print(e)
    Base.metadata.create_all(bind=engine)
except Exception as e:
    print(e)
    sys.exit(0)