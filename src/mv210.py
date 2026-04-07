from pymodbus.client import ModbusTcpClient

from config import (
    MV210_IP,
    MV210_PORT,
    MV210_UNIT,
    MV210_DI1_COUNTER_ADDR,
    MV210_DI3_PERIOD_ADDR,
)


class MV210Client:
    def __init__(self):
        self.client = ModbusTcpClient(MV210_IP, port=MV210_PORT)

    def connect(self):
        if not self.client.connect():
            raise RuntimeError("Connection to MV210 failed")

    def disconnect(self):
        try:
            self.client.close()
        except Exception:
            pass

    def is_connected(self) -> bool:
        return bool(getattr(self.client, "socket", None))

    @staticmethod
    def _u32_from_regs_swapped_words(regs):
        """
        МВ210 отдает UINT32 как [low_word, high_word]
        """
        if len(regs) != 2:
            raise ValueError(f"Expected 2 registers, got {len(regs)}")
        low_word = regs[0]
        high_word = regs[1]
        return (high_word << 16) | low_word

    def read_u32(self, address: int) -> int:
        rr = self.client.read_holding_registers(
            address=address,
            count=2,
            device_id=MV210_UNIT,
        )
        if rr.isError():
            raise RuntimeError(f"Modbus read error at {address}: {rr}")
        return self._u32_from_regs_swapped_words(rr.registers)

    def read_di1_counter(self) -> int:
        return self.read_u32(MV210_DI1_COUNTER_ADDR)

    def read_di3_period_ms(self) -> int:
        return self.read_u32(MV210_DI3_PERIOD_ADDR)