import snap7
from snap7.util import get_real
from config import PLC_IP, PLC_RACK, PLC_SLOT

class PLCReader:
    def __init__(self):
        self.client = snap7.client.Client()

    def connect(self):
        if not self.client.get_connected():
            self.client.connect(PLC_IP, PLC_RACK, PLC_SLOT)

    def disconnect(self):
        if self.client.get_connected():
            self.client.disconnect()

    def is_connected(self) -> bool:
        return self.client.get_connected()

    def read_real(self, db_number: int, offset: int) -> float:
        data = self.client.db_read(db_number, offset, 4)
        return get_real(data, 0)

    def read_raw_currents(self) -> dict:
        return {
            "db1_current_ma": self.read_real(1, 20),
            "db2_current_ma": self.read_real(2, 20),
            "db3_current_ma": self.read_real(3, 20),
            "db6_current_ma": self.read_real(6, 20),
            "db8_current_ma": self.read_real(8, 20),
            "db9_current_ma": self.read_real(9, 20),
        }
