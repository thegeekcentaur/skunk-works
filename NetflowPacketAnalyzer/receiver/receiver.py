import asyncio
import socket
import struct
from datetime import datetime
import time
from typing import Dict, Any, Tuple
from functools import wraps
import os


def async_timeit(func):
    """
    A decorator to measure the execution time of an asynchronous function.
    """
    @wraps(func)
    async def wrapper(*args, **kwargs):
        start_time = time.perf_counter()
        result = await func(*args, **kwargs)  # Await the coroutine
        end_time = time.perf_counter()
        total_time = end_time - start_time
        print(f"    Function: '{func.__name__}', time(seconds): {total_time:.8f}")
        return result
    return wrapper


# By default, expect the Rust module to be available, but fall back to Python oterhwise
RUST_AVAILABLE = (os.getenv('RUST_AVAILABLE', 'True').lower() == 'true')
if RUST_AVAILABLE:
    try:
        import netflow_processor
        RUST_AVAILABLE = True
        print("Rust netflow_processor module loaded successfully")
    except ImportError as e:
        print(f"Rust module not available ({e}), using Python fallback")
        RUST_AVAILABLE = False
print(f"Rust module is disabled (via settings), using Python fallback")

class NetflowReceiver:
    def __init__(self, host: str = '0.0.0.0', port: int = 2055):
        self.host = host
        self.port = port
        self.transport = None
        self.packet_count = 0
        self.rust_processing_enabled = RUST_AVAILABLE
        self.rust_success_count = 0
        self.python_fallback_count = 0

    async def start_server(self):
        """Start the UDP server to listen for netflow packets"""
        print(f"Starting netflow receiver on {self.host}:{self.port}")
        
        loop = asyncio.get_event_loop()
        self.transport, protocol = await loop.create_datagram_endpoint(
            lambda: NetflowProtocol(self.handle_packet),
            local_addr=(self.host, self.port)
        )
        print(f"Receiver listening on {self.host}:{self.port}")
    
    @async_timeit
    async def handle_packet(self, data: bytes, addr: Tuple[str, int]):
        """Handle received netflow packet - now calls Rust module directly"""
        try:
            self.packet_count += 1
            
            if self.rust_processing_enabled:
                # Try Rust processing first
                success = await self.process_with_rust(data, addr[0], addr[1], self.packet_count)
                if success:
                    self.rust_success_count += 1
                    return
                else:
                    # Fallback to Python if Rust fails
                    print(f"Falling back to Python processing for packet #{self.packet_count}")
            
            # Python fallback processing
            await self.process_with_python(data, addr, self.packet_count)
            self.python_fallback_count += 1
            
        except Exception as e:
            print(f"Error processing packet from {addr}: {e}")

    async def process_with_rust(self, data: bytes, source_addr: str, source_port: int, packet_number: int) -> bool:
        """Process packet using Rust module"""
        try:
            # Call the Rust function directly - no subprocess needed!
            output = netflow_processor.process_packet_rust(data, source_addr, source_port, packet_number)
            print(output, end='')  # Rust already includes newlines
            return True
        except Exception as e:
            print(f"Rust processing failed: {e}")
            return False

    async def process_with_python(self, data: bytes, addr: Tuple[str, int], packet_number: int):
        """Python fallback processing"""
        try:
            packet_info = self.parse_netflow_packet(data)
            await self.process_packet_python(packet_info, addr, packet_number)
        except Exception as e:
            print(f"Python fallback processing failed: {e}")

    def parse_netflow_packet(self, data: bytes) -> Dict[str, Any]:
        """Parse netflow v5 packet (fallback Python implementation)"""
        if len(data) < 24:
            raise ValueError("Packet too short for netflow header")
            
        # Parse netflow v5 header
        header = struct.unpack('!HHIIIIBBH', data[:24])
    
        packet_info = {
            'version': header[0],
            'count': header[1],
            'sys_uptime': header[2],
            'unix_secs': header[3],
            'unix_nsecs': header[4],
            'flow_sequence': header[5],
            'engine_type': header[6],
            'engine_id': header[7],
            'sampling_interval': header[8],
            'timestamp': datetime.fromtimestamp(header[3]),
            'flows': []
        }
        
        # Parse individual flow records (48 bytes each for v5)
        flow_data = data[24:]
        flow_count = min(header[1], len(flow_data) // 48)
        
        for i in range(flow_count):
            offset = i * 48
            flow_bytes = flow_data[offset:offset + 48]
            if len(flow_bytes) >= 48:
                flow = self.parse_flow_record(flow_bytes)
                packet_info['flows'].append(flow)
                
        return packet_info

    def parse_flow_record(self, data: bytes) -> Dict[str, Any]:
        """Parse a single netflow v5 flow record (fallback Python implementation)"""
        # Netflow v5 flow record format (48 bytes) - must match sender format
        # flow = struct.unpack('!IIIHHIIIIHHBBBBHHBB', data)
        # Netflow v5 flow record format (48 bytes) - must match sender format
        flow = struct.unpack('!IIIHHIIIIHHBBBBHHBBH', data)
        
        return {
            'srcaddr': socket.inet_ntoa(struct.pack('!I', flow[0])),
            'dstaddr': socket.inet_ntoa(struct.pack('!I', flow[1])),
            'nexthop': socket.inet_ntoa(struct.pack('!I', flow[2])),
            'input_snmp': flow[3],
            'output_snmp': flow[4],
            'packets': flow[5],
            'bytes': flow[6],
            'first': flow[7],
            'last': flow[8],
            'srcport': flow[9],
            'dstport': flow[10],
            'pad1': flow[11],
            'tcp_flags': flow[12],
            'protocol': flow[13],
            'tos': flow[14],
            'src_as': flow[15],
            'dst_as': flow[16],
            'src_mask': flow[17],
            'dst_mask': flow[18],
            'pad2': flow[19],
        }

    async def process_packet_python(self, packet_info: Dict[str, Any], addr: Tuple[str, int], packet_number: int):
        """Process and display received netflow packet (fallback Python implementation)"""
        print(f"\n{'='*70}")
        print(f"Netflow Packet #{packet_number} received from {addr[0]}:{addr[1]} (Python fallback)")
        print(f"Timestamp: {packet_info['timestamp']}")
        print(f"Version: {packet_info['version']}, Flow count: {packet_info['count']}")
        print(f"Sequence: {packet_info['flow_sequence']}")
        print(f"System uptime: {packet_info['sys_uptime']} ms")
        
        for i, flow in enumerate(packet_info['flows'], 1):
            protocol_name = self.get_protocol_name(flow['protocol'])
            print(f"\n Flow {i}:")
            print(f"   Source: {flow['srcaddr']}:{flow['srcport']}")
            print(f"   Destination: {flow['dstaddr']}:{flow['dstport']}")
            print(f"   Protocol: {protocol_name} ({flow['protocol']})")
            print(f"   Packets: {flow['packets']:,}, Bytes: {flow['bytes']:,}")
            print(f"   TCP Flags: 0x{flow['tcp_flags']:02x}")
            print(f"   AS Path: {flow['src_as']} → {flow['dst_as']}")
            print(f"   Next Hop: {flow['nexthop']}")
        
        print(f"{'='*70}")
    
    def get_protocol_name(self, protocol_num: int) -> str:
        """Convert protocol number to name"""
        if RUST_AVAILABLE:
            try:
                return netflow_processor.get_protocol_name(protocol_num)
            except:
                pass
        
        # Python fallback
        protocols = {
            1: 'ICMP',
            6: 'TCP',
            17: 'UDP',
            47: 'GRE',
            50: 'ESP',
            51: 'AH',
            89: 'OSPF'
        }
        return protocols.get(protocol_num, f'Unknown({protocol_num})')

    async def process_flows(self):
        """Main processing function that waits for incoming flows"""
        print("=== Starting Flow Processing ===")
        
        if self.rust_processing_enabled:
            print("Rust processing: ENABLED")
            
            # Test the Rust module with a simple call
            try:
                test_protocol = netflow_processor.get_protocol_name(6)
                print(f"Rust module test: TCP = {test_protocol}")
            except Exception as e:
                print(f"Rust module test failed: {e}")
                self.rust_processing_enabled = False
        else:
            print("Rust processing: DISABLED (using Python fallback)")
        
        await self.start_server()
        
        try:
            # Keep the server running
            while True:
                await asyncio.sleep(10)
                # Print processing statistics every 10 seconds
                if self.packet_count > 0:
                    print(f"Stats: Total={self.packet_count}, Rust={self.rust_success_count}, Python={self.python_fallback_count}")
        except KeyboardInterrupt:
            print("\n Receiver interrupted by user")
            print(f"Final Stats: Total={self.packet_count}, Rust={self.rust_success_count}, Python={self.python_fallback_count}")
        finally:
            await self.stop_server()

    async def stop_server(self):
        """Stop the server gracefully"""
        if self.transport:
            self.transport.close()
            print("🔌 Server stopped")

class NetflowProtocol(asyncio.DatagramProtocol):
    """UDP protocol handler for netflow packets"""
    def __init__(self, packet_handler):
        self.packet_handler = packet_handler
        
    def datagram_received(self, data, addr):
        """Called when a UDP datagram is received"""
        asyncio.create_task(self.packet_handler(data, addr))

# Advanced Rust integration functions
def demonstrate_rust_features():
    """Demonstrate advanced features of the Rust module"""
    if not RUST_AVAILABLE:
        print("Rust module not available for demonstration")
        return
    
    try:
        # Create some test data
        test_data = bytes.fromhex('000500010000303965f8f7e70000000000000001000000c0a8016400000a000001c0a801010001000200000000000005dc000003e8000007d00050001bb0001800060000fde9fde20018180000')
        
        print("\n=== Rust Module Demonstration ===")
        
        # Parse packet using Rust
        packet = netflow_processor.parse_netflow_packet(test_data, "192.168.1.100", 12345, 1)
        print(f"Parsed packet: {packet}")
        print(f"Header: {packet.header}")
        print(f"Flows: {len(packet.flows)}")
        
        if packet.flows:
            flow = packet.flows[0]
            print(f"First flow: {flow}")
            print(f"Protocol name: {flow.get_protocol_name()}")
        
        # Test direct processing
        output = netflow_processor.process_packet_rust(test_data, "192.168.1.100", 12345, 1)
        print("Direct processing output:")
        print(output)
        
    except Exception as e:
        print(f"Rust demonstration failed: {e}")

async def main():
    """Main function that starts the event loop and waits on process_flows"""
    print("=== Netflow Receiver Container with PyO3 Rust Processing ===")

    # Get configuration from environment or use defaults
    listen_host = os.getenv('LISTEN_HOST', '0.0.0.0')
    listen_port = int(os.getenv('LISTEN_PORT', '2055'))

    # Demonstrate Rust features if available
    if os.getenv('DEMO_RUST', 'false').lower() == 'true':
        demonstrate_rust_features()

    receiver = NetflowReceiver(listen_host, listen_port)

    try:
        # Main event loop waits on process_flows
        await receiver.process_flows()
    except Exception as e:
        print(f"Receiver error: {e}")

if __name__ == "__main__":
    # Start the asyncio event loop
    asyncio.run(main())
