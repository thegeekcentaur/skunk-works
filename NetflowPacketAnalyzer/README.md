## Problem Statement

The idea here is to build a python application with an asyncio event loop. 
This event loop awaits messages to be sent from a function called `process_flows`, and prints them out.
This function is however CPU-intensive, so it has been decided that part of this function needs to be re-written to a new language of our choice. 
Eventually the solution becomes a python function calling a pre-compiled code which helps off-load the heavy computing/processing.

## Solution Description In Brief

- Prefer a docker-based set-up which is portable and consistent
- Create a pair of containers, one mimicing the NetFlow packet sender, and the other one being the receiver
- Within receiver, create functions to process the inbound packets, and time the over-all processing
- Off-load the processing functions to a pre-compiled module built on a more performant programming language
- __*Rust*__ was chosen to be the language of choice here, since
    * it offers __zero-cost abstractions and no garbage collection (GC)__, resulting in minimal overhead
    * for packet processing, Rust's fine-grained memory control ensures consistent low-latency execution for raw compute tasks.
    * it works better for binary parsing + aggregation, benefitting from its system-level optimizations
- In order to couple the Rust library to the Python application, `pyo3` was introduced, and the docker image for receiver was built in multi-stage 

## How To Run

- Check out the repository
- Change directory to `NetflowPacketAnalyzer` in the terminal, i.e., ``` cd NetflowPacketAnalyzer```
- Run
  ```bash
  docker compose up --build
  ```
- To compare performance between the original Python code, and the pre-compiled Rust module, set the environment variable __RUST_AVAILBLE__ to __True__ under `NetflowPacketAnalyzer\docker-compose.yml`
     * Note the timing details in the terminal, once the containers start running.
     * Example -
       ```bash
       Function: 'handle_packet', time(seconds): 0.00018552
       ```
