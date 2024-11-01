use clap::Parser;
use ipc_channel_adapter::child::sync::*;
use ipc_channel_adapter::host::sync::*;
use std::thread;
use std::time;

#[derive(Parser, Debug)]
struct Config {
    #[arg(short, long, default_value_t = 1000)]
    messages: usize,
    #[arg(short, long, default_value_t = false)]
    debug: bool,
}

// run child process that does nothing but retuning what it received
fn run_child(
    channel_host_in: &str,
    channel_host_out: &str,
    debug: bool,
) -> anyhow::Result<thread::JoinHandle<()>> {
    let _host_sender = HostSender::<usize, usize>::new(channel_host_in).unwrap();

    let (_host_receiver, host_receiver_rx) =
        HostReceiver::<usize, usize>::new(channel_host_out).unwrap();

    let handle = thread::spawn(move || {
        while let Ok((v, reply)) = host_receiver_rx.recv() {
            if debug {
                println!("[Child] Received: {}", v);
            }
            reply.send(v).unwrap();
        }
    });

    Ok(handle)
}

pub fn main() -> Result<(), String> {
    let Config {
        messages,
        debug,
    } = Config::parse();
    let expected = messages;

    let child_sender = ChildSender::<usize, usize>::new()?;

    let (child_receiver, _child_rx) = ChildReceiver::<usize, usize>::new()?;

    println!("Starting: child");
    let _child_handle = run_child(
        &child_receiver.server_name,
        &child_sender.server_name,
        debug,
    )
    .unwrap();

    println!("Benchmark: host sending {}", messages);

    let mut total = 0;

    let start_time = time::SystemTime::now();
    for _ in 0..messages {
        let result = child_sender.send_blocking(1)?;
        total += result;
    }
    let end_time = start_time.elapsed().unwrap();

    assert_eq!(expected, total, "Sums don't match");

    println!("Successfully roundtrip {}", messages);
    println!("took: {:.3}s", end_time.as_millis() as f32 / 1000 as f32);

    Ok(())
}
