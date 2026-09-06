import numpy as np
from labjack import ljm
from .channels import StreamChannel

''' Setup a periodic stream on a single output channel.

Similar to a standard stream, using an ljm call that handles looping and simplifies setup.

https://support.labjack.com/docs/periodicstreamout-ljm-user-s-guide

USAGE:
Use .add(data, target, scan_rate, [buffer_index]) for up to 4 streams.
- Buffser_index 0:3 store the output data.
- Scan_rate must be the same for all adds.
Start streaming with .start()
Stop with .stop()
The scan rate is retained between start/stop. 


NOTE: PeriodicStreamOut set STREAM_OUT#(0:3)_BUFFER_ALLOCATE_NUM_BYTES to 16384.

NOTE: The following registers are configurated automatically and SHOULD NOT be updated manually!
STREAM_OUT#(0:3)_TARGET
STREAM_OUT#(0:3)_BUFFER_ALLOCATE_NUM_BYTES
STREAM_OUT#(0:3)_LOOP_NUM_VALUES
STREAM_OUT#(0:3)_ENABLE
STREAM_OUT#(0:3)_BUFFER_U16
STREAM_OUT#(0:3)_SET_LOOP


'''


class WaveformGenerator:
    def __init__(self, labjack):
        self.labjack = labjack
        self.scan_list = []
        self.scan_and_target_list:list[tuple[int,int]] = [] # list[tuple
        self.scan_rate = 0
        self.scans_per_read_div = 1 # this has no impact on output only; only impacts buffering reads

    # def reset(self):
    #     self.scan_list = []
    #     self.scan_rate = 0
    #     # for index in range(4):     # T7 has STREAM_OUT0 through STREAM_OUT3
    #     #     ljm.eWriteName(self.labjack.handle, f"STREAM_OUT{index}_ENABLE", 0)

    def add(self, 
            data:list, 
            target:StreamChannel|str, 
            scan_rate:int,
            stream_out_index:int = 0,
        ):
        ''' 
        Setup a periodic output stream on output device 'target' using buffer stream_out_index.

        LJM_PeriodicStreamOut(
            int Handle,
            int StreamOutIndex,
            int TargetAddr,
            double ScanRate,
            int NumValues,
            const double * aWriteData)
        '''
        self.stop()

        if stream_out_index<0 or stream_out_index>3:
            raise ValueError(f'Stream buffer {stream_out_index} invalid, must be 0:3')
        self.stream_out_index = stream_out_index

        if self.scan_rate == 0:
            self.scan_rate = scan_rate
            # reset to allow re-use of module
            # for index in range(4):  
            #     ljm.eWriteName( self.labjack.handle, f"STREAM_OUT{index}_ENABLE", 0)
            # disable streams
            aRst = dict()
            for i in range(4):
                aRst[f"STREAM_OUT{i}_ENABLE"] = 0
            ljm.eWriteNames(self.labjack.handle, 
                len(aRst), list(aRst.keys()), list(aRst.values()))        
            # clear buffers
            aRst = dict()
            for i in range(4):
                aRst[f"STREAM_OUT{i}_BUFFER_ALLOCATE_NUM_BYTES"] = 0
                #aRst[f"STREAM_OUT{i}_LOOP_NUM_VALUES"] = 0
            ljm.eWriteNames(self.labjack.handle, 
                len(aRst), list(aRst.keys()), list(aRst.values()))        
            
        if self.scan_rate != scan_rate:
            raise ValueError(f"Scan rate must be same for all waveforms")

        target_addr = ljm.nameToAddress(target)[0]
        scan_addr   = ljm.nameToAddress(f'STREAM_OUT{stream_out_index}')[0]
        self.scan_list.append(scan_addr)
        self.scan_and_target_list.append((stream_out_index, target_addr))

        ljm.periodicStreamOut(
            handle         = self.labjack.handle,
            streamOutIndex = stream_out_index,
            targetAddr     = target_addr,
            scanRate       = self.scan_rate,
            numValues      = len(data),
            aWriteData     = data
        ) 

    def add_many(self, data:list[list], targets:list[StreamChannel|str], stream_out_indexes:list[int], scan_rate:int):
        if (len(data) != len(targets)) or (len(data) != len(stream_out_indexes)):
            raise ValueError("Length of data, targets, and stream_out_indexes must match")
        for d, t, i in zip(data, targets, stream_out_indexes):
            self.add(d, t, stream_out_index=i, scan_rate=scan_rate)
        return
    

#    def start(self, scan_rate:int|None=None, scans_per_read_div:int|None=None):
    def start(self):
        self.stop()

        if self.scans_per_read_div < 1:
            raise ValueError(f"Scan per read (divisor) must be positive integer, {self.scans_per_read_div} is invalid")
        if  self.scan_rate > self._device_scanRate()*len(self.scan_list):
            print(f'WARNING: ScanRate {self.scan_rate} for {len(self.scan_list)} self.scan_rate')
            return

        ljm.eStreamStart(
            handle = self.labjack.handle,
            scansPerRead = self.scan_rate // self.scans_per_read_div,
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
        return

    #TODO Refactor this to core
    def _device_scanRate(self) -> int:
        if self.labjack.device_type == ljm.constants.dtT7:
            return 100000
        else:
            raise ValueError("Only labjack T7 supported")


