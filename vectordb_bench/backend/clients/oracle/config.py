from pydantic import SecretStr

from ..api import DBConfig

class OracleConfig(DBConfig):
    password: SecretStr
    user: str
    wallet_password: SecretStr
    dsn: str
    wallet_location: str
    config_dir: str


    def to_dict(self) -> dict:
        return {
            "user":self.user,
            "password": self.password.get_secret_value(),
            "dsn": self.dsn,
            "config_dir": self.config_dir,
            "wallet_location": self.wallet_location,
            "wallet_password": self.wallet_password.get_secret_value(),
            "orcl":True
        }
    
# this is based on the chroma version... adapt it for ADB using TLSv (i.e. without zip.)