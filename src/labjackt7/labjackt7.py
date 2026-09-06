''' Base LabJack class implementing device connection and communication. '''
from labjack import ljm
from labjackt7 import Analog, Digital, Temperature, PWM, SPI, I2C, Stream, WaveformGenerator, PatternGenerator

class LabjackT7():
    def __init__(self, device='T7', connection='ANY', device_identifier='ANY', verbose=True):
        '''
        device: T7 (default) or T4
        connection: ethernet, usb...
        device_identifier: serial num...
        '''
        self.device_type = None
        self.serial_number = None
        try:
            self.handle = ljm.openS(
                device,
                connection,
                device_identifier
            )
            info = ljm.getHandleInfo(self.handle)
            if info[0] not in [ljm.constants.dtT7, ljm.constants.dtT4]:
                raise ValueError(f'Unsupported LabJack device type: {info[0]}')
        except Exception as e:
            print(f'Failed to connect to LabJack ({connection} {device_identifier}): {e}.')
            raise
        self.device_type = info[0]
        self.connection_type = info[1]
        self.serial_number = info[2]
        self.ip_address = ljm.numberToIP(info[3])
        self.port = info[4]
        self.bytes_per_MB = info[5]
        self.firmware_version = ljm.eReadName(self.handle, "FIRMWARE_VERSION")
        self.ljtick = None # hack until tick support is added

        if verbose:
            print(f'Connected to LabJack type {self.device_type}')
            print(f'  Connection type {self.connection_type}')
            print(f'  Serial number {self.serial_number}')
            print(f'  IP Address {self.ip_address}')
            print(f'  Port {self.port}')

        ## load submodules
        self.analog = Analog(self)
        self.digital = Digital(self)
        self.temperature = Temperature(self)
        self.pwm = PWM(self)
        self.spi = SPI(self)
        self.i2c = I2C(self)
        self.stream = Stream(self)
        self.waveform = WaveformGenerator(self)
        self.pattern = PatternGenerator(self)

    def _query(self, register):
        ''' Reads the specified register. '''
        return ljm.eReadName(self.handle, register)

    def _read_array(self, register, num_bytes):
        return ljm.eReadNameByteArray(self.handle, register, num_bytes)

    def _command(self, register, value):
        ''' Writes a value to a specified register.

            Args:
                register (str): a Modbus register on the LabJack.
                value: the value to write to the register.
                '''
        ljm.eWriteName(self.handle, register, value)

    def _write(self, **kwargs):
        ''' Updates registers according to the passed keyword arguments. For
            example, to set DAC0 to 1 and DAC1 to 0 we would call
                self._write(DAC0=1, DAC1=0)
        '''
        self._write_array(list(kwargs.keys()), list(kwargs.values()))

    def _write_array(self, registers, values):
        ljm.eWriteNames(self.handle, len(registers), registers, values)

    def _write_dict(self, d):
        ''' Writes values to registers according to the passed dictionary. '''
        self._write_array(list(d.keys()), list(d.values()))

    def _device_scanRate(self) -> int:
        if self.device_type == ljm.constants.dtT7:
            return 100000
        elif self.device_type == ljm.constants.dtT4:
            return 40000
        print("ERROR - device type unknown, cannot determine scan rate")
        return 40000


    def stop(self):
        ''' Stop streaming if currently running '''
        try:
            ljm.eStreamStop(self.handle)
        except Exception:
            pass

if __name__ == '__main__':
    lj = LabjackT7()
