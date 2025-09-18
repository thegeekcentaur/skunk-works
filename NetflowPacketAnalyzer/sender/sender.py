import asyncio
import socket
import struct
from datetime import datetime
import random
import os

class NetflowSender:
    def __init__(self, target_host: str = 'receiver', target_port: int = 2055):
        self.target_host = target_host
        self.target_port = target_port
        self.sequence = 1

    def create_netflow_packet(self) -> bytes:
        """Create a sample netflow v5 packet"""
        # Generate random flow data for more realistic testing
        src_ip = f"192.168.1.{random.randint(1, 254)}"
        dst_ip = f"10.0.0.{random.randint(1, 254)}"
        src_port = random.randint(1024, 65535)
        dst_port = random.choice([80, 443, 22, 25, 53, 8080])
        protocol = random.choice([6, 17, 1])  # TCP, UDP, ICMP
        packets = random.randint(1, 100)
        bytes_count = packets * random.randint(64, 1500)
        
        # Create netflow v5 header
        header = struct.pack('!HHIIIIBBH', 
            5,          # version
            1,          # count (1 flow record)
            random.randint(10000, 99999),  # sys_uptime
            int(datetime.now().timestamp()),  # unix_secs
            0,          # unix_nsecs
            self.sequence,  # flow_sequence
            0,          # engine_type
            0,          # engine_id
            0           # sampling_interval
        )
        
        # Create flow record (netflow v5 format - 48 bytes total)
        # Build it step by step to avoid struct format issues
        flow = b''
        flow += struct.pack('!I', struct.unpack('!I', socket.inet_aton(src_ip))[0])     # srcaddr (4)
        flow += struct.pack('!I', struct.unpack('!I', socket.inet_aton(dst_ip))[0])     # dstaddr (4)  
        flow += struct.pack('!I', struct.unpack('!I', socket.inet_aton('192.168.1.1'))[0]) # nexthop (4)
        flow += struct.pack('!H', 1)           # input_snmp (2)
        flow += struct.pack('!H', 2)           # output_snmp (2)
        flow += struct.pack('!I', packets)     # packets (4)
        flow += struct.pack('!I', bytes_count) # bytes (4)
        flow += struct.pack('!I', 1000)        # first (4)
        flow += struct.pack('!I', 2000)        # last (4)
        flow += struct.pack('!H', src_port)    # srcport (2)
        flow += struct.pack('!H', dst_port)    # dstport (2)
        flow += struct.pack('!B', 0)           # pad1 (1)
        flow += struct.pack('!B', 0x18)        # tcp_flags (1)
        flow += struct.pack('!B', protocol)    # protocol (1)
        flow += struct.pack('!B', 0)           # tos (1)
        flow += struct.pack('!H', 65001)       # src_as (2)
        flow += struct.pack('!H', 65002)       # dst_as (2)
        flow += struct.pack('!B', 24)          # src_mask (1)
        flow += struct.pack('!B', 24)          # dst_mask (1)
        flow += struct.pack('!H', 0)           # pad2 (2)
        # Total: 48 bytes
        
        self.sequence += 1
        return header + flow

    async def send_packets(self):
        """Continuously send netflow packets to receiver"""
        print(f"Starting netflow sender to {self.target_host}:{self.target_port}")
        
        # Wait a bit for receiver to be ready
        await asyncio.sleep(5)
        
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        
        try:
            packet_count = 0
            while True:
                try:
                    packet = self.create_netflow_packet()
                    sock.sendto(packet, (self.target_host, self.target_port))
                    packet_count += 1
                    
                    print(f"Sent packet {packet_count} to {self.target_host}:{self.target_port}")
                    print(f"  Sequence: {self.sequence - 1}")
                    print(f"  Size: {len(packet)} bytes")
                    
                    # Sleep for 1-5 seconds at random before sending next packet
                    await asyncio.sleep(random.randint(1, 5))
                    
                except socket.gaierror as e:
                    print(f"DNS resolution error: {e}")
                    print("Retrying in 5 seconds...")
                    await asyncio.sleep(5)
                except Exception as e:
                    print(f"Error sending packet: {e}")
                    await asyncio.sleep(2)
                    
        except KeyboardInterrupt:
            print("\nSender interrupted by user")
        finally:
            sock.close()
            print("Sender stopped")


async def main():
    """Main function for sender container"""
    print("=== Netflow Sender Container ===")

    # Get target from environment or use default
    target_host = os.getenv('RECEIVER_HOST', 'receiver')
    target_port = int(os.getenv('RECEIVER_PORT', '2055'))

    sender = NetflowSender(target_host, target_port)

    try:
        await sender.send_packets()
    except Exception as e:
        print(f"Sender error: {e}")


if __name__ == "__main__":
    asyncio.run(main())
