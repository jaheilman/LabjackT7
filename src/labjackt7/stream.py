from labjack import ljm
# from .core import LabjackT7
# from scipy.signal import resample
import numpy as np
from datetime import datetime

class StreamConfig():
    def __init__(self, settling_time=0, resolution_index=0, clock_source=0):
        self.settling_time = settling_time
        self.resolution_index = resolution_index
        self.clock_source = clock_source

    def to_dict(self):
        return {
            'STREAM_SETTLING_US': self.settling_time,
            'STREAM_RESOLUTION_INDEX': self.resolution_index,
            'STREAM_CLOCK_SOURCE': self.clock_source,
        }

class Stream():
    def __init__(self, labjack, config: StreamConfig | None = None):
        self.labjack = labjack
        if isinstance(config, StreamConfig):
            self.config = config
            self.configure_options(self.config)
        else:
            self.configure()

    def configure(self, settling_time=0, resolution_index=0, clock_source=0):
        self.config = StreamConfig(
            settling_time=settling_time,
            resolution_index=resolution_index,
            clock_source=clock_source,
        )
        self.configure_options(self.config)

    def configure_options(self, stream_options: dict | StreamConfig):
        self.stop()
        if isinstance(stream_options, StreamConfig):
            self.labjack._write_dict(stream_options.to_dict())
        else:
            self.labjack._write_dict(stream_options)

    def set_inhibit(self, channels):
        bitmask = self.labjack.digital.bitmask(channels)
        inhibit = 0x7FFFFF-bitmask

        self.labjack._write_dict({
            'DIO_INHIBIT': inhibit,
            'DIO_DIRECTION': bitmask
        })

    def stop(self):
        ''' Stop streaming if currently running '''
        try:
            ljm.eStreamStop(self.labjack.handle)
        except:
            pass

    #disabled because removed scipy.signal.resample()
    # def resample(self, array, period, max_samples = 8191):
    #     ''' Compute optimum scan rate and number of samples '''
    #     max_speed = self._device_scanRate()
    #     cutoff = max_samples / max_speed
    #     if period >= cutoff:
    #         samples = max_samples
    #         scanRate = int(samples/period)
    #     else:
    #         scanRate = max_speed
    #         samples = int(period*scanRate)
    #     # stream = resample(array, samples)
    #     stream = []
    #     scanRate /= array.shape[1]    ## divide by number of channels being streamed
    #     return stream, scanRate

    def stream_burst(self, aScanListNames:list, scanRate:int=0, scanTime_s:float=1) -> tuple[int,list]:
        ''' 
            Args:
                scanListNames: ["AIN0", "AIN1"] etc
                scan_rate: 0 for max rate
                scan_time_s: number of seconds to sample (default 1)
        '''
        aScanList = ljm.namesToAddresses(len(aScanListNames), aScanListNames)[0]  # Names to addresses for streamBurst
        if (scanRate <= 0) or (scanRate > self._device_scanRate()):
            scanRate = self._device_scanRate()
        num_scans = int(scanTime_s*scanRate)  # Number of scans to perform
        num_scans = num_scans - (num_scans % len(aScanList)) # ensure all channels have equal samples
        start = datetime.now()
        scanRate, aData = ljm.streamBurst(self.labjack.handle, len(aScanList), aScanList, scanRate, num_scans)
        end = datetime.now()
        if False:
            print(f"Channels: {len(aScanListNames)},  Samples per Ch: {len(aData)/len(aScanListNames)}, ScanRate: {scanRate}, Elapsed Time = {(end - start).seconds + float((end - start).microseconds) / 1000000}s" )
        if aData.count(-9999.0) > 0:
            print(f"WARNING: some samples were skipped! Total skips, all channels) = f{aData.count(-9999.0)}")
        return scanRate, self._reshape_data(aData, len(aScanList))

    def stream_start(self, channels:list, scan_rate, scans_per_read=None, stream_out=None):
        return self.stream_in_out(
            input_channels=channels,
            scan_rate=scan_rate,
            scans_per_read=scans_per_read,
            stream_out=stream_out,
        )

    def stream_read(self):
        return ljm.eStreamRead(self.labjack.handle)

    def aout(self, channels, data, scanRate, loop=0):
        array = np.asarray(data)
        if array.ndim == 1:
            if len(channels) != 1:
                raise ValueError("Analog stream-out data must have one column per output channel.")
            output_data = [array]
        elif array.ndim == 2 and array.shape[1] == len(channels):
            output_data = [array[:, i] for i in range(array.shape[1])]
        else:
            raise ValueError("Analog stream-out data must be 1-D for one channel or 2-D with one column per channel.")

        self.stream_in_out(
            input_channels=[],
            scan_rate=scanRate,
            scans_per_read=1,
            stream_out=[
                {
                    'target': 1000 + 2*ch,
                    'data': output_data[i],
                    'dtype': 'F32',
                    'loop': loop,
                }
                for i, ch in enumerate(channels)
            ],
        )

    def dout(self, data, scanRate, loop=0):
        self.stream_in_out(
            input_channels=[],
            scan_rate=scanRate,
            scans_per_read=1,
            stream_out=[{
                'target': 2500,
                'data': data,
                'dtype': 'U16',
                'loop': loop,
            }],
        )

    def stream_in_out(self, input_channels:list, scan_rate, scans_per_read=None, stream_out=None):
        self.stop()
        stream_out = stream_out or []
        scan_list = list(ljm.namesToAddresses(len(input_channels), input_channels)[0]) if input_channels else []

        for index, output in enumerate(stream_out):
            self._configure_stream_out(index, output)
            scan_list.append(4800 + index)

        if not scan_list:
            raise ValueError("At least one input or output channel is required to start stream mode.")

        if scans_per_read is None:
            scans_per_read = max(1, int(scan_rate / 2))

        return ljm.eStreamStart(
            self.labjack.handle,
            scans_per_read,
            len(scan_list),
            scan_list,
            scan_rate,
        )

    def _configure_stream_out(self, index, output):
        target = output['target']
        data = self._stream_out_values(output['data'])
        dtype = output.get('dtype', 'F32')
        loop = output.get('loop', 0)
        buffer_num_bytes = self._stream_out_buffer_num_bytes(len(data))

        self.labjack._write_dict({
            f'STREAM_OUT{index}_ENABLE': 0,
            f'STREAM_OUT{index}_TARGET': target,
            f'STREAM_OUT{index}_BUFFER_ALLOCATE_NUM_BYTES': buffer_num_bytes,
            f'STREAM_OUT{index}_ENABLE': 1
        })

        registers = [f'STREAM_OUT{index}_BUFFER_{dtype}'] * len(data)
        self.labjack._write_array(registers, data)

        loop_num_values = len(data) if loop else 0
        self.labjack._write_dict({
            f'STREAM_OUT{index}_LOOP_NUM_VALUES': loop_num_values,
            f'STREAM_OUT{index}_SET_LOOP': 1
        })

    def _stream_out_values(self, data):
        array = np.asarray(data)
        if array.ndim == 0:
            return [array.item()]
        if array.ndim == 1:
            return array.tolist()
        if array.ndim == 2 and array.shape[1] == 1:
            return array[:, 0].tolist()
        raise ValueError("Stream-out data must be one-dimensional per output channel.")

    def _stream_out_buffer_num_bytes(self, num_values):
        if num_values <= 0:
            raise ValueError("Stream-out data must contain at least one value.")
        min_buffer_bytes = 2 * (num_values + 1)
        exponent = int(np.ceil(np.log2(min_buffer_bytes)))
        return int(2 ** exponent)

    def set_trigger(self, ch):
        if ch is None:
            self.labjack._command("STREAM_TRIGGER_INDEX", 0) # disable triggered stream
        else:
            self.labjack._write_dict({
                f"DIO{ch}_EF_ENABLE": 0
            })
            self.labjack._write_dict({
                f"DIO{ch}_EF_INDEX": 3,
                f"DIO{ch}_EF_OPTIONS": 12,   ## current value: 0 (PWM Out)
                # f"DIO{ch}_EF_VALUE_A": 2,
                f"DIO{ch}_EF_CONFIG_A": 1,
                f"DIO{ch}_EF_CONFIG_B": 1,
                f"DIO{ch}_EF_ENABLE": 1,
                "STREAM_TRIGGER_INDEX": 2000+ch
            })
            ljm.writeLibraryConfigS('LJM_STREAM_RECEIVE_TIMEOUT_MS',0)  #disable timeout

    def _device_scanRate(self) -> int:
        if self.labjack.device_type == ljm.constants.dtT7:
            return 100000
        elif self.labjack.device_type == ljm.constants.dtT4:
            return 40000
        print("ERROR - device type unknown, cannot determine scan rate")
        return 40000

    def _reshape_data(self, aData:list, num_channels:int):
        ''' splits scan data into list of lists'''
        channels = []
        ch = []
        for i in range(num_channels):
            ch = aData[i:][::num_channels]
            channels.append(ch)
        return channels
