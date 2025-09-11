// rust_processor/src/lib.rs
use byteorder::{BigEndian, ReadBytesExt};
use chrono::{DateTime, NaiveDateTime, Utc};
use pyo3::prelude::*;
use std::io::Cursor;
use std::net::Ipv4Addr;

#[pyclass]
#[derive(Debug, Clone)]
pub struct NetflowHeader {
    #[pyo3(get)]
    pub version: u16,
    #[pyo3(get)]
    pub count: u16,
    #[pyo3(get)]
    pub sys_uptime: u32,
    #[pyo3(get)]
    pub unix_secs: u32,
    #[pyo3(get)]
    pub unix_nsecs: u32,
    #[pyo3(get)]
    pub flow_sequence: u32,
    #[pyo3(get)]
    pub engine_type: u8,
    #[pyo3(get)]
    pub engine_id: u8,
    #[pyo3(get)]
    pub sampling_interval: u16,
    #[pyo3(get)]
    pub timestamp: String,
}

#[pymethods]
impl NetflowHeader {
    fn __repr__(&self) -> PyResult<String> {
        Ok(format!(
            "NetflowHeader(version={}, count={}, sequence={})",
            self.version, self.count, self.flow_sequence
        ))
    }
}

#[pyclass]
#[derive(Debug, Clone)]
pub struct FlowRecord {
    #[pyo3(get)]
    pub srcaddr: String,
    #[pyo3(get)]
    pub dstaddr: String,
    #[pyo3(get)]
    pub nexthop: String,
    #[pyo3(get)]
    pub input_snmp: u16,
    #[pyo3(get)]
    pub output_snmp: u16,
    #[pyo3(get)]
    pub packets: u32,
    #[pyo3(get)]
    pub bytes: u32,
    #[pyo3(get)]
    pub first: u32,
    #[pyo3(get)]
    pub last: u32,
    #[pyo3(get)]
    pub srcport: u16,
    #[pyo3(get)]
    pub dstport: u16,
    #[pyo3(get)]
    pub pad1: u8,
    #[pyo3(get)]
    pub tcp_flags: u8,
    #[pyo3(get)]
    pub protocol: u8,
    #[pyo3(get)]
    pub tos: u8,
    #[pyo3(get)]
    pub src_as: u16,
    #[pyo3(get)]
    pub dst_as: u16,
    #[pyo3(get)]
    pub src_mask: u8,
    #[pyo3(get)]
    pub dst_mask: u8,
    #[pyo3(get)]
    pub pad2: u8,
}

#[pyclass]
#[derive(Debug, Clone)]
pub struct NetflowPacket {
    #[pyo3(get)]
    pub header: NetflowHeader,
    #[pyo3(get)]
    pub flows: Vec<FlowRecord>,
    #[pyo3(get)]
    pub source_addr: String,
    #[pyo3(get)]
    pub source_port: u16,
    #[pyo3(get)]
    pub packet_number: u32,
}

#[pymethods]
impl NetflowPacket {
    fn __repr__(&self) -> PyResult<String> {
        Ok(format!(
            "NetflowPacket(#{}, from {}:{}, {} flows)",
            self.packet_number, self.source_addr, self.source_port, self.flows.len()
        ))
    }

    fn print_packet_info(&self) -> PyResult<String> {
        let mut output = String::new();
        
        output.push_str(&format!("\n{}\n", "=".repeat(70)));
        output.push_str(&format!(
            "Netflow Packet #{} received from {}:{}\n",
            self.packet_number, self.source_addr, self.source_port
        ));
        output.push_str(&format!(" Timestamp: {}\n", self.header.timestamp));
        output.push_str(&format!(
            "Version: {}, Flow count: {}\n",
            self.header.version, self.header.count
        ));
        output.push_str(&format!(" Sequence: {}\n", self.header.flow_sequence));
        output.push_str(&format!("  System uptime: {} ms\n", self.header.sys_uptime));

        for (i, flow) in self.flows.iter().enumerate() {
            let protocol_name = flow.get_protocol_name().unwrap_or_else(|_| format!("Unknown({})", flow.protocol));
            output.push_str(&format!("\n Flow {}:\n", i + 1));
            output.push_str(&format!("   Source: {}:{}\n", flow.srcaddr, flow.srcport));
            output.push_str(&format!("   Destination: {}:{}\n", flow.dstaddr, flow.dstport));
            output.push_str(&format!("   Protocol: {} ({})\n", protocol_name, flow.protocol));
            output.push_str(&format!("   Packets: {:}, Bytes: {:}\n", flow.packets, flow.bytes));
            output.push_str(&format!("   TCP Flags: 0x{:02x}\n", flow.tcp_flags));
            output.push_str(&format!("   AS Path: {} → {}\n", flow.src_as, flow.dst_as));
            output.push_str(&format!("   Next Hop: {}\n", flow.nexthop));
        }

        output.push_str(&format!("{}\n", "=".repeat(70)));
        Ok(output)
    }
}

fn parse_netflow_packet_internal(
    data: &[u8],
    source_addr: &str,
    source_port: u16,
    packet_number: u32,
) -> PyResult<NetflowPacket> {
    if data.len() < 24 {
        return Err(pyo3::exceptions::PyValueError::new_err(
        "Packet too short for netflow header",
    ));
    }

    let mut cursor = Cursor::new(data);

    // Parse header
    let version = cursor
        .read_u16::<BigEndian>()
        .map_err(|e| pyo3::exceptions::PyValueError::new_err(format!("Error reading version: {}", e)))?;
    let count = cursor
        .read_u16::<BigEndian>()
        .map_err(|e| pyo3::exceptions::PyValueError::new_err(format!("Error reading count: {}", e)))?;
    let sys_uptime = cursor
        .read_u32::<BigEndian>()
        .map_err(|e| pyo3::exceptions::PyValueError::new_err(format!("Error reading sys_uptime: {}", e)))?;
    let unix_secs = cursor
        .read_u32::<BigEndian>()
        .map_err(|e| pyo3::exceptions::PyValueError::new_err(format!("Error reading unix_secs: {}", e)))?;
    let unix_nsecs = cursor
        .read_u32::<BigEndian>()
        .map_err(|e| pyo3::exceptions::PyValueError::new_err(format!("Error reading unix_nsecs: {}", e)))?;
    let flow_sequence = cursor
        .read_u32::<BigEndian>()
        .map_err(|e| pyo3::exceptions::PyValueError::new_err(format!("Error reading flow_sequence: {}", e)))?;
    let engine_type = cursor
        .read_u8()
        .map_err(|e| pyo3::exceptions::PyValueError::new_err(format!("Error reading engine_type: {}", e)))?;
    let engine_id = cursor
        .read_u8()
        .map_err(|e| pyo3::exceptions::PyValueError::new_err(format!("Error reading engine_id: {}", e)))?;
    let sampling_interval = cursor
        .read_u16::<BigEndian>()
        .map_err(|e| pyo3::exceptions::PyValueError::new_err(format!("Error reading sampling_interval: {}", e)))?;

    // Create timestamp string (simplified without pyo3-chrono)
    let timestamp = if unix_secs > 0 {
        let dt = DateTime::<Utc>::from_utc(
            NaiveDateTime::from_timestamp_opt(unix_secs as i64, 0).unwrap_or_default(),
            Utc,
        );
        dt.format("%Y-%m-%d %H:%M:%S UTC").to_string()
    } else {
        "Invalid timestamp".to_string()
    };

    let header = NetflowHeader {
        version,
        count,
        sys_uptime,
        unix_secs,
        unix_nsecs,
        flow_sequence,
        engine_type,
        engine_id,
        sampling_interval,
        timestamp,
    };

    // Parse flow records
    let mut flows = Vec::new();
    let flow_data = &data[24..];
    let flow_count = std::cmp::min(count as usize, flow_data.len() / 48);

    for i in 0..flow_count {
        let offset = i * 48;
        if offset + 48 <= flow_data.len() {
            let flow_bytes = &flow_data[offset..offset + 48];
            match parse_flow_record_internal(flow_bytes) {
                Ok(flow) => flows.push(flow),
                Err(e) => {
                    return Err(pyo3::exceptions::PyValueError::new_err(format!(
                        "Error parsing flow {}: {}",
                        i, e
                    )))
                }
            }
        }
    }

    Ok(NetflowPacket {
        header,
        flows,
        source_addr: source_addr.to_string(),
        source_port,
        packet_number,
    })
}

fn parse_flow_record_internal(data: &[u8]) -> Result<FlowRecord, String> {
    if data.len() < 48 {
    return Err("Flow record too short".to_string());
    }

    let mut cursor = Cursor::new(data);

    let srcaddr_raw = cursor
        .read_u32::<BigEndian>()
        .map_err(|e| format!("Error reading srcaddr: {}", e))?;
    let dstaddr_raw = cursor
        .read_u32::<BigEndian>()
        .map_err(|e| format!("Error reading dstaddr: {}", e))?;
    let nexthop_raw = cursor
        .read_u32::<BigEndian>()
        .map_err(|e| format!("Error reading nexthop: {}", e))?;

    let srcaddr = Ipv4Addr::from(srcaddr_raw).to_string();
    let dstaddr = Ipv4Addr::from(dstaddr_raw).to_string();
    let nexthop = Ipv4Addr::from(nexthop_raw).to_string();

    let input_snmp = cursor
        .read_u16::<BigEndian>()
        .map_err(|e| format!("Error reading input_snmp: {}", e))?;
    let output_snmp = cursor
        .read_u16::<BigEndian>()
        .map_err(|e| format!("Error reading output_snmp: {}", e))?;
    let packets = cursor
        .read_u32::<BigEndian>()
        .map_err(|e| format!("Error reading packets: {}", e))?;
    let bytes = cursor
        .read_u32::<BigEndian>()
        .map_err(|e| format!("Error reading bytes: {}", e))?;
    let first = cursor
        .read_u32::<BigEndian>()
        .map_err(|e| format!("Error reading first: {}", e))?;
    let last = cursor
        .read_u32::<BigEndian>()
        .map_err(|e| format!("Error reading last: {}", e))?;
    let srcport = cursor
        .read_u16::<BigEndian>()
        .map_err(|e| format!("Error reading srcport: {}", e))?;
    let dstport = cursor
        .read_u16::<BigEndian>()
        .map_err(|e| format!("Error reading dstport: {}", e))?;
    let pad1 = cursor
        .read_u8()
        .map_err(|e| format!("Error reading pad1: {}", e))?;
    let tcp_flags = cursor
        .read_u8()
        .map_err(|e| format!("Error reading tcp_flags: {}", e))?;
    let protocol = cursor
        .read_u8()
        .map_err(|e| format!("Error reading protocol: {}", e))?;
    let tos = cursor
        .read_u8()
        .map_err(|e| format!("Error reading tos: {}", e))?;
    let src_as = cursor
        .read_u16::<BigEndian>()
        .map_err(|e| format!("Error reading src_as: {}", e))?;
    let dst_as = cursor
        .read_u16::<BigEndian>()
        .map_err(|e| format!("Error reading dst_as: {}", e))?;
    let src_mask = cursor
        .read_u8()
        .map_err(|e| format!("Error reading src_mask: {}", e))?;
    let dst_mask = cursor
        .read_u8()
        .map_err(|e| format!("Error reading dst_mask: {}", e))?;
    let pad2 = cursor
        .read_u8()
        .map_err(|e| format!("Error reading pad1: {}", e))?;

    Ok(FlowRecord {
        srcaddr,
        dstaddr,
        nexthop,
        input_snmp,
        output_snmp,
        packets,
        bytes,
        first,
        last,
        srcport,
        dstport,
        pad1,
        tcp_flags,
        protocol,
        tos,
        src_as,
        dst_as,
        src_mask,
        dst_mask,
        pad2,
    })

}

#[pyfunction]
fn parse_netflow_packet(
    data: &[u8],
    source_addr: &str,
    source_port: u16,
    packet_number: u32,
) -> PyResult<NetflowPacket> {
    parse_netflow_packet_internal(data, source_addr, source_port, packet_number)
}

#[pyfunction]
fn get_protocol_name(protocol_num: u8) -> PyResult<String> {
    let protocol_name = match protocol_num {
        1 => "ICMP",
        6 => "TCP",
        17 => "UDP",
        47 => "GRE",
        50 => "ESP",
        51 => "AH",
        89 => "OSPF",
        _ => return Ok(format!("Unknown({})", protocol_num)),
    };
    Ok(protocol_name.to_string())
}

#[pyfunction]
fn process_packet_rust(
    data: &[u8],
    source_addr: &str,
    source_port: u16,
    packet_number: u32,
) -> PyResult<String> {
    let packet = parse_netflow_packet_internal(data, source_addr, source_port, packet_number)?;
    packet.print_packet_info()
}

#[pymodule]
fn netflow_processor(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(parse_netflow_packet, m)?)?;
    m.add_function(wrap_pyfunction!(get_protocol_name, m)?)?;
    m.add_function(wrap_pyfunction!(process_packet_rust, m)?)?;
    m.add_class::<NetflowHeader>()?;
    m.add_class::<FlowRecord>()?;
    m.add_class::<NetflowPacket>()?;
    Ok(())
}

#[pymethods]
impl FlowRecord {
    fn __repr__(&self) -> PyResult<String> {
        Ok(format!(
            "FlowRecord({}:{} -> {}:{}, proto={}, packets={})",
            self.srcaddr, self.srcport, self.dstaddr, self.dstport, self.protocol, self.packets
        ))
    }

    fn get_protocol_name(&self) -> PyResult<String> {
        let protocol_name = match self.protocol {
            1 => "ICMP",
            6 => "TCP",
            17 => "UDP",
            47 => "GRE",
            50 => "ESP",
            51 => "AH",
            89 => "OSPF",
            _ => return Ok(format!("Unknown({})", self.protocol)),
        };
        Ok(protocol_name.to_string())
    }
}
