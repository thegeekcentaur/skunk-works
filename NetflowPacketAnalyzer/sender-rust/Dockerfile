FROM rust:1.89

WORKDIR /app

COPY Cargo.toml Cargo.toml
COPY src src

RUN cargo build --release

CMD ["./target/release/netflow-rustic-sender"]