import logging
from contextlib import contextmanager
from typing import Any
import array
import oracledb
import json
from collections.abc import Iterable

print('packages loaded')

from ..api import DBCaseConfig, DBConfig, EmptyDBCaseConfig, IndexType, VectorDB

log = logging.getLogger(__name__)

class Oracle(VectorDB):
    ''' Oracle client for VectorDB '''

    def __init__(self,dim:int,db_config: dict,drop_old: bool = False,timeout: int = 30,**kwargs,):
        self.db_config = db_config
        client = oracledb.connect(user=self.db_config['user'],password=self.db_config['password'],dsn=self.db_config['dsn'],wallet_location=self.db_config['wallet_location'],wallet_password=self.db_config['wallet_password'],config_dir=self.db_config['config_dir'])
        self.timeout = 30
        self.orcl = self.db_config['orcl']
        if drop_old:
            with client.cursor() as cursor:
                cursor.execute('DROP TABLE IF EXISTS VDBB')
                cursor.execute('CREATE TABLE VDBB (ID VARCHAR2(100),METADATA VARCHAR2(1000),EMBEDDING VECTOR)')
        client.close()

    def orcl(self):
        print('db is oracle')
        return True


    @classmethod
    def case_config_cls(cls, index_type: IndexType | None = None) -> type[DBCaseConfig]:
        return EmptyDBCaseConfig


    @contextmanager
    def init(self) -> None:
        #client = oracledb.connect(user=self.db_config['user'],password=self.db_config['password'],dsn=self.db_config['dsn'],wallet_location=self.db_config['wallet_location'],wallet_password=self.db_config['wallet_password'],config_dir=self.db_config['config_dir'])
        #print('client created')
        # drop existing vectordb table
        try:
            self.client = oracledb.connect(user=self.db_config['user'],password=self.db_config['password'],dsn=self.db_config['dsn'],wallet_location=self.db_config['wallet_location'],wallet_password=self.db_config['wallet_password'],config_dir=self.db_config['config_dir'])
            self.cursor = self.client.cursor()
        except oracledb.Error as e:
            print(f"Error connecting to the database: {e}")
            self.client = None
            self.cursor = None
        yield



        #with oracledb.connect(user=self.db_config['user'],password=self.db_config['password'],dsn=self.db_config['dsn'],wallet_location=self.db_config['wallet_location'],wallet_password=self.db_config['wallet_password'],config_dir=self.db_config['config_dir']) as client:
        #    with client.cursor() as cursor:
                #yield
        
    def ready_to_search(self):
        pass

    def optimize():
        pass

 #   def addDocument(connection,cursor,table_name,record):
 #       cursor.execute(f"""INSERT  INTO {table_name} (ID, EMBEDDING,METADATA) VALUES (:id, :embedding, :metadata)""",{"id": record["id"],"embedding" : array.array("d",record["embedding"]),"metadata" : record["metadata"],})
 #       connection.commit()

    def insert_embeddings( self,
        embeddings: Iterable[list[float]],
        metadata: list[int],
        **kwargs: Any,) -> tuple[int,Exception]:
        ''' creates a new table and inserts embeddings. Note there are better ways to do this '''
        print('starting embeddings')
        assert len(embeddings) == len(metadata)
        insert_count = 0
        for i in range(len(embeddings)):
            record = {'id':str(i),'embedding':embeddings[i],'metadata':str(metadata[i])}
            try:
                self.cursor.execute(f"""INSERT  INTO VDBB (ID, EMBEDDING,METADATA) VALUES (:id, :embedding, :metadata)""",{"id": record["id"],"embedding" : array.array("d",record["embedding"]),"metadata" : record["metadata"],})
                self.client.commit()
            except:
                with oracledb.connect(user=self.db_config['user'],password=self.db_config['password'],dsn=self.db_config['dsn'],wallet_location=self.db_config['wallet_location'],wallet_password=self.db_config['wallet_password'],config_dir=self.db_config['config_dir']) as client:
                    with client.cursor() as cursor:
                        cursor.execute(f"""INSERT  INTO VDBB (ID, EMBEDDING,METADATA) VALUES (:id, :embedding, :metadata)""",{"id": record["id"],"embedding" : array.array("d",record["embedding"]),"metadata" : record["metadata"],})
                        client.commit()
            insert_count+=1
        return len(embeddings), None

    def search_embedding(self,query: list[float],k:int = 100,filters: dict | None = None,**kwargs: Any,):
        print('starting vector search')
        embedding_arr_j = json.dumps(query)
        print('query prepared')
        id_value = filters.get("id")
        if filters:
            query = f"""
            SELECT id,
                text,
                metadata,
                vector_distance(embedding, :embedding,COSINE) as distance
            FROM VDBB
            WHERE id > {id_value}
            ORDER BY distance
            FETCH APPROX FIRST {k} ROWS ONLY"""
        else:
            query = f"""
            SELECT id,
                text,
                metadata,
                vector_distance(embedding, :embedding,COSINE) as distance
            FROM VDBB
            ORDER BY distance
            FETCH APPROX FIRST {k} ROWS ONLY"""

        # Execute the query
        print('running search')
        try:
            self.cursor.execute(query, embedding=embedding_arr_j)
            results = self.cursor.fetchall()
        except:
            with oracledb.connect(user=self.db_config['user'],password=self.db_config['password'],dsn=self.db_config['dsn'],wallet_location=self.db_config['wallet_location'],wallet_password=self.db_config['wallet_password'],config_dir=self.db_config['config_dir']) as client:
                with client.cursor() as cursor:
                    cursor.execute(query, embedding=embedding_arr_j)
                    results = cursor.fetchall()
        print('search results',results)
        return results

    def __reduce__(self):
        """Custom pickling behavior."""
        # Return the information needed to reconstruct the client *without*
        # the active connection and cursor.
        return (
            self.__class__,
            tuple([self.db_config]),  # Arguments for __init__
            self.__getstate__()  # State to be restored
        )

    def __getstate__(self):
        """Return the state of the object to be pickled."""
        # We explicitly exclude the connection and cursor from the pickled state.
        state = self.__dict__.copy()
        state['client'] = None
        state['cursor'] = None
        return state

    def __setstate__(self, state):
        """Restore the object's state upon unpickling."""
        self.__dict__.update(state)
        # Re-establish the connection and cursor when the object is unpickled.
        self.init(self.db_config)