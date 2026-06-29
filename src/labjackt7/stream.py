from labjack import ljm
import numpy as np
from datetime import datetime
from .channels import StreamChannels

'''
Streaming 

Streaming requires a single scan rate (and clock and trigger source).

Up to 128 channels can be scanned while streaming.
Up to 4 channels can be outputs (limited by stream buffers).
Total output buffer size is 64k (of UINT16 words), by default each channel gets 16k.


Outputs are prepared with LJM_PeriodicStreamOut, which connects an output port (target) with data buffer (stream_out_index).
LJM_PeriodicStreamOut(
    int Handle,
    int StreamOutIndex,
    int TargetAddr,
    double ScanRate,
    int NumValues,
    const double * aWriteData)

'''


class StreamConfig():
    def __init__(self, scan_rate:int=100000, reads_per_scan:int=1, settling_time:int=0, resolution_index:int=0, clock_source:int=0):
        self.scan_rate:int = scan_rate
        self.reads_per_scan:int = reads_per_scan
        self.settling_time:int = settling_time
        self.resolution_index:int = resolution_index
        self.clock_source:int = clock_source
        self.scan_list = []

    def to_dict(self):
        return {
            'SCAN_RATE': self.scan_rate,
            'READS_PER_SCAN': self.reads_per_scan,
            'STREAM_SETTLING_US': self.settling_time,
            'STREAM_RESOLUTION_INDEX': self.resolution_index,
            'STREAM_CLOCK_SOURCE': self.clock_source,
        }

class Stream():
    def __init__(self, labjack):
        self.labjack = labjack
        self.scan_rate:int        = self._device_scanRate()
        self.reads_per_scan:int   = 1
        self.settling_time:int    = 0
        self.resolution_index:int = 0
        self.clock_source:int     = 0
        self.scan_list:list       = []


    def configure(self, scan_rate:int=100000, reads_per_scan:int=1, settling_time=0, resolution_index=0, clock_source=0):
        self.scan_rate        = scan_rate
        self.reads_per_scan   = reads_per_scan
        self.settling_time    = settling_time
        self.resolution_index = resolution_index
        self.clock_source     = clock_source
        self.scan_list        = []
        # todo:
        # STREAM_BUFFER_SIZE_BYTES
        # max RAM 64k, buffer max is 32k (32768).  Default it 4096.  values are 16 bit

    # def start(self, channels:list, scan_rate:int):
    #     self.stop()
    #     scan_list = ljm.namesToAddresses(len(channels), channels)[0]
    #     scans_per_read = int(scan_rate/2)
    #     ljm.eStreamStart(self.labjack.handle, scans_per_read, len(channels), scan_list, scan_rate)

    def start(self):
        self.stop()
        ljm.eStreamStart(
            handle = self.labjack.handle,
            scansPerRead = self.scan_rate // self.reads_per_scan,
            numAddresses = len(self.scan_list),
            aScanList = self.scan_list,
            scanRate = self.scan_rate
        )
        return


    def stop(self):
        ''' Stop streaming if currently running '''
        try:
            ljm.eStreamStop(self.labjack.handle)
        except:
            pass


    def read(self):
        return ljm.eStreamRead(self.labjack.handle)


    def add_output(self, data:list, target:StreamChannels|str, stream_out_index:int = 0):
        ''' 
        Setup a periodic output stream on output device 'target' using buffer stream_out_index.

        This supports generic targets, DAC0/1, FIO_STATE/DIRECTION (aka the whole FIO buffer)
        Supported targets are enumerated in .channels.StreamChannels
        '''
        self.stream_out_index = stream_out_index

        target_addr = ljm.nameToAddress(target)[0]
        scan_addr   = ljm.nameToAddress(f'STREAM_OUT{stream_out_index}')[0]
        self.scan_list.append(scan_addr)

        if (self.scan_rate <= 0) or (self.scan_rate > self._device_scanRate()*len(self.scan_list)):
            print(f'WARNING: ScanRate {self.scan_rate} for {len(self.scan_list)} channels is invalid')

        ljm.periodicStreamOut(
            handle         = self.labjack.handle,
            streamOutIndex = stream_out_index,
            targetAddr     = target_addr,
            scanRate       = self.scan_rate,
            numValues      = len(data),
            aWriteData     = data
        ) 
        return
    

    def add_outputs(self, data:list[list], targets:list[StreamChannels|str], stream_out_indexes:list[int]):
        if (len(data) != len(targets)) or (len(data) != len(stream_out_indexes)):
            raise ValueError("Length of data, targets, and stream_out_indexes must match")
        for d, t, i in zip(data, targets, stream_out_indexes):
            self.add_output(d, t, i)
        return


    def ain(self, channels:list, scanRate:int=0 ):


    # def aout(self, channels, data, scanRate, loop=0):
    #     ''' aout() is meant to simplify streaming output.
    #     This is already simple, since the only channels are DAC0 and DAC1, just use add_output[s]
    #     '''
    #     array = np.asarray(data)
    #     if array.ndim == 1:
    #         if len(channels) != 1:
    #             raise ValueError("Analog stream-out data must have one column per output channel.")
    #         output_data = [array]
    #     elif array.ndim == 2 and array.shape[1] == len(channels):
    #         output_data = [array[:, i] for i in range(array.shape[1])]
    #     else:
    #         raise ValueError("Analog stream-out data must be 1-D for one channel or 2-D with one column per channel.")

    #     self.stream_in_out(
    #         input_channels=[],
    #         scan_rate=scanRate,
    #         scans_per_read=1,
    #         stream_out=[
    #             {
    #                 'target': 1000 + 2*ch,
    #                 'data': output_data[i],
    #                 'dtype': 'F32',
    #                 'loop': loop,
    #             }
    #             for i, ch in enumerate(channels)
    #         ],
    #     )


    def dout(self, data, scanRate, loop=0):
        ''' 
        dout is mean to simplify digital output streaming by converting a single, named Digital I/O channel
        (e.g. FIO0) into the full-port bitmask and direction used by the stream engine.
        '''
        #todo: finish
        return


    # 
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


    # def stream_in_out(self, input_channels:list, scan_rate, scans_per_read=None, stream_out=None):
    #     self.stop()
    #     stream_out = stream_out or []
    #     scan_list = list(ljm.namesToAddresses(len(input_channels), input_channels)[0]) if input_channels else []

    #     for index, output in enumerate(stream_out):
    #         self._configure_stream_out(index, output)
    #         scan_list.append(4800 + index)

    #     if not scan_list:
    #         raise ValueError("At least one input or output channel is required to start stream mode.")

    #     if scans_per_read is None:
    #         scans_per_read = max(1, int(scan_rate / 2))

    #     return ljm.eStreamStart(
    #         self.labjack.handle,
    #         scans_per_read,
    #         len(scan_list),
    #         scan_list,
    #         scan_rate,
    #     )

    # def _configure_stream_out(self, index, output):
    #     target = output['target']
    #     data = self._stream_out_values(output['data'])
    #     dtype = output.get('dtype', 'F32')
    #     loop = output.get('loop', 0)
    #     buffer_num_bytes = self._stream_out_buffer_num_bytes(len(data))

    #     self.labjack._write_dict({
    #         f'STREAM_OUT{index}_ENABLE': 0,
    #         f'STREAM_OUT{index}_TARGET': target,
    #         f'STREAM_OUT{index}_BUFFER_ALLOCATE_NUM_BYTES': buffer_num_bytes,
    #     })

    #     registers = [f'STREAM_OUT{index}_BUFFER_{dtype}'] * len(data)
    #     self.labjack._write_array(registers, data)

    #     loop_num_values = len(data) if loop else 0
    #     self.labjack._write_dict({
    #         f'STREAM_OUT{index}_LOOP_NUM_VALUES': loop_num_values,
    #         f'STREAM_OUT{index}_SET_LOOP': 1,
    #         f'STREAM_OUT{index}_ENABLE': 1,
    #     })


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
        # elif self.labjack.device_type == ljm.constants.dtT4:
        #     return 40000
        raise ValueError("ERROR - device type must be T7")


    def _reshape_data(self, aData:list, num_channels:int):
        ''' splits scan data into list of lists'''
        channels = []
        ch = []
        for i in range(num_channels):
            ch = aData[i:][::num_channels]
            channels.append(ch)
        return channels


    def _write_config(self, stream_options: dict | StreamConfig):
        self.stop()
        if isinstance(stream_options, StreamConfig):
            self.labjack._write_dict(stream_options.to_dict())
        else:
            self.labjack._write_dict(stream_options)


    def _set_inhibit(self, channels):
        bitmask = self.labjack.digital.bitmask(channels)
        inhibit = 0x7FFFFF-bitmask

        self.labjack._write_dict({
            'DIO_INHIBIT': inhibit,
            'DIO_DIRECTION': bitmask
        })
