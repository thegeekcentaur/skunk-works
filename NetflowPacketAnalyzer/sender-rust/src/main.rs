use std::env;
use std::error::Error;
use std::net::SocketAddr;
use std::time::Duration;

use byteorder::{BigEndian, WriteBytesExt};
use chrono::Utc;
use rand::seq::SliceRandom;
use rand::Rng;
use tokio::net::{lookup_host, UdpSocket};

#[derive(Debug)]
struct NetFlowSender {
    target_host: String,
    target_port: u16,
    sequence: u32,
}

impl NetFlowSender {
    fn new(target_host: String, target_port: u16) -> Self {
        Self {
            target_host,
            target_port,
            sequence: 1,
        }
    }

    fn create_netflow_packet(&mut self) -> Vec<u8> {
        let mut rng = rand::thread_rng();

        let src_ip_str = format!("192.168.2.{}", rng.gen_range(1..=254));
        let dst_ip_str = format!("10.0.1.{}", rng.gen_range(1..=254));
        let src_port: u16 = rng.gen_range(1024..=65535);
        let dst_ports = [80u16, 443, 22, 25, 53, 8080];
        let dst_port = *dst_ports.choose(&mut rng).unwrap();
        let protocols = [6u8, 17, 1];
        let protocol = *protocols.choose(&mut rng).unwrap();
        let packets: u32 = rng.gen_range(1..=100);
        let bytes_count: u32 = packets * rng.gen_range(64..=1500);

        // Header (24 bytes)
        let mut header = vec![0u8; 24];
        let mut w = &mut header[..];
        w.write_u16::<BigEndian>(5).unwrap(); // version
        w.write_u16::<BigEndian>(1).unwrap(); // count
        w.write_u32::<BigEndian>(rng.gen_range(10000..=99999)).unwrap(); // sys_uptime
        w.write_u32::<BigEndian>(Utc::now().timestamp() as u32).unwrap(); // unix_secs
        w.write_u32::<BigEndian>(0).unwrap(); // unix_nsecs
        w.write_u32::<BigEndian>(self.sequence).unwrap(); // flow_sequence
        w.write_u8(0).unwrap(); // engine_type
        w.write_u8(0).unwrap(); // engine_id
        w.write_u16::<BigEndian>(0).unwrap(); // sampling_interval

        // Flow record (48 bytes)
        let mut flow = vec![0u8; 48];
        let mut wf = &mut flow[..];

        // IPs as u32 in network byte order
        let src_ip_bytes = src_ip_str.parse::<std::net::Ipv4Addr>().unwrap().octets();
        wf.write_u32::<BigEndian>(u32::from_be_bytes(src_ip_bytes)).unwrap();
        let dst_ip_bytes = dst_ip_str.parse::<std::net::Ipv4Addr>().unwrap().octets();
        wf.write_u32::<BigEndian>(u32::from_be_bytes(dst_ip_bytes)).unwrap();
        let next_hop_str = "192.168.2.1";
        let next_hop_bytes = next_hop_str.parse::<std::net::Ipv4Addr>().unwrap().octets();
        wf.write_u32::<BigEndian>(u32::from_be_bytes(next_hop_bytes)).unwrap();
        wf.write_u16::<BigEndian>(1).unwrap(); // input_snmp
        wf.write_u16::<BigEndian>(2).unwrap(); // output_snmp
        wf.write_u32::<BigEndian>(packets).unwrap(); // packets
        wf.write_u32::<BigEndian>(bytes_count).unwrap(); // bytes
        wf.write_u32::<BigEndian>(1000).unwrap(); // first
        wf.write_u32::<BigEndian>(2000).unwrap(); // last
        wf.write_u16::<BigEndian>(src_port).unwrap(); // srcport
        wf.write_u16::<BigEndian>(dst_port).unwrap(); // dstport
        wf.write_u8(0).unwrap(); // pad1
        wf.write_u8(0x18).unwrap(); // tcp_flags
        wf.write_u8(protocol).unwrap(); // protocol
        wf.write_u8(0).unwrap(); // tos
        wf.write_u16::<BigEndian>(65001).unwrap(); // src_as
        wf.write_u16::<BigEndian>(65002).unwrap(); // dst_as
        wf.write_u8(24).unwrap(); // src_mask
        wf.write_u8(24).unwrap(); // dst_mask
        wf.write_u16::<BigEndian>(0).unwrap(); // pad2

        self.sequence += 1;

        let mut packet = header;
        packet.extend_from_slice(&flow);
        packet
    }

    async fn send_packets(&mut self) {
        println!(
            "Starting netflow sender to {}:{}",
            self.target_host, self.target_port
        );

        tokio::time::sleep(Duration::from_secs(5)).await;

        let sock = match UdpSocket::bind("0.0.0.0:0").await {
            Ok(s) => s,
            Err(e) => {
                println!("Failed to bind UDP socket: {}", e);
                return;
            }
        };

        let mut packet_count = 0;

        loop {
            let resolve_str = format!("{}:{}", self.target_host, self.target_port);
            let target_addr: SocketAddr = match lookup_host(&resolve_str).await {
                Ok(mut addrs) => match addrs.next() {
                    Some(addr) => addr,
                    None => {
                        println!("No IP addresses found for {}", self.target_host);
                        println!("Retrying in 5 seconds...");
                        tokio::time::sleep(Duration::from_secs(5)).await;
                        continue;
                    }
                },
                Err(e) => {
                    println!("DNS resolution error: {}", e);
                    println!("Retrying in 5 seconds...");
                    tokio::time::sleep(Duration::from_secs(5)).await;
                    continue;
                }
            };

            let packet = self.create_netflow_packet();

            match sock.send_to(&packet, target_addr).await {
                Ok(_) => {
                    packet_count += 1;
                    println!(
                        "Sent packet {} to {}:{}",
                        packet_count, self.target_host, self.target_port
                    );
                    println!("  Sequence: {}", self.sequence - 1);
                    println!("  Size: {} bytes", packet.len());
                }
                Err(e) => {
                    println!("Error sending packet: {}", e);
                    tokio::time::sleep(Duration::from_secs(2)).await;
                    continue;
                }
            }

            let sleep_sec = rand::thread_rng().gen_range(1..=5);
            tokio::time::sleep(Duration::from_secs(sleep_sec)).await;
        }
    }
}

#[tokio::main]
async fn main() -> Result<(), Box<dyn Error>> {
    println!("=== Netflow Sender Container ===");

    let target_host = env::var("RECEIVER_HOST").unwrap_or_else(|_| "receiver".to_string());
    let target_port_str = env::var("RECEIVER_PORT").unwrap_or_else(|_| "2055".to_string());
    let target_port: u16 = target_port_str.parse()?;

    let mut sender = NetFlowSender::new(target_host, target_port);

    sender.send_packets().await;

    Ok(())
}