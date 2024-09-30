import re
import sys
import matplotlib.colors as mcolors
import mplcursors
import plotly.graph_objs as go
from plotly.subplots import make_subplots


class Thread:
    def __init__(self, pid, cpu, timestamp):
        self.pid = pid
        self.cpu = cpu
        self.creation_timestamp = timestamp
        self.termination_timestamp = 1
        self.events = []
        self.away_time = 0
        self.running = False
        self.switches = []

    def migrate(self, timestamp, new_cpu):
        self.events.append((timestamp, self.cpu, new_cpu))
        self.cpu = new_cpu

    def switch_away(self, timestamp):
        self.switches.append((self.away_time, timestamp))
        self.running = False
    def switch_back(self, timestamp):
        if not self.running:
            self.away_time = timestamp
            self.running = True
           

    def terminate(self, timstamp):
        self.termination_timestamp = timstamp


    def __repr__(self):
        return f"Thread(pid={self.pid}, created on={self.creation_timestamp} events={self.events} switches:{self.switches})"

def parse_line(line):
    exec_pattern = re.compile(
        r'\s*(\S+)-(\d+)\s+\[(\d+)\]\s+.*?\s+(\d+\.\d+): sched_process_exec:\s+filename=(\S+)\s+pid=(\d+)\s+old_pid=(\d+)'
    )
    fork_pattern = re.compile(
        r'\s*(\S+)-(\d+)\s+\[(\d+)\]\s+.*?\s+(\d+\.\d+): sched_process_fork:\s+comm=(\S+)\s+pid=(\d+)\s+child_comm=(\S+)\s+child_pid=(\d+)'
    )
    migrate_pattern = re.compile(
        r'\s*(\S+)-(\d+)\s+\[\d+\]\s+.*?\s+(\d+\.\d+): sched_migrate_task:\s+comm=(\S+)\s+pid=(\d+)\s+prio=(\d+)\s+orig_cpu=(\d+)\s+dest_cpu=(\d+)'
    )
    switch_pattern = re.compile(
        r'\s*(\S+)-(\d+)\s+\[(\d+)\]\s+.*?\s+(\d+\.\d+): sched_switch:\s+(\S+):(\d+) \[\d+\] \S+ ==> (\S+):(\d+) \[\d+\]'
    )
    exit_pattern = re.compile(
        r'\s*(\S+)-(\d+)\s+\[(\d+)\]\s+.*?\s+(\d+\.\d+): sched_process_exit:\s+comm=(\S+)\s+pid=(\d+)\s+prio=(\d+)'
    )
    wakeup_pattern = re.compile(
        r'\s*(\S+)-(\d+)\s+\[(\d+)\]\s+.*?\s+(\d+\.\d+): sched_wakeup:\s+(\S+):(\d+)\s+\[\d+\]\s+CPU:(\d+)'
    )

    exec_match = exec_pattern.match(line)
    if exec_match:
        return {
            "type": "sched_process_exec",
            "timestamp": float(exec_match.group(4)),
            "pid": int(exec_match.group(6)),
            "cpu": int(exec_match.group(3)),
            "filename": exec_match.group(5),
        }

    fork_match = fork_pattern.match(line)
    if fork_match:
        return {
            "type": "sched_process_fork",
            "timestamp": float(fork_match.group(4)),
            "pid": int(fork_match.group(6)),
            "cpu": int(fork_match.group(3)),
            "child_pid": int(fork_match.group(8)),
        }

    migrate_match = migrate_pattern.match(line)
    if migrate_match:
        return {
            "type": "sched_migrate_task",
            "timestamp": float(migrate_match.group(3)),
            "pid": int(migrate_match.group(5)),
            "cpu": int(migrate_match.group(8)),
        }

    switch_match = switch_pattern.match(line)
    if switch_match:
        return {
            "type": "sched_switch",
            "timestamp": float(switch_match.group(4)),
            "cpu": int(switch_match.group(3)),
            "prev_comm": switch_match.group(5),
            "prev_pid": int(switch_match.group(6)),
            "next_comm": switch_match.group(7),
            "next_pid": int(switch_match.group(8)),
        }

    exit_match = exit_pattern.match(line)
    if exit_match:
        return {
            "type": "sched_process_exit",
            "timestamp": float(exit_match.group(4)),
            "pid": int(exit_match.group(6)),
            "comm": exit_match.group(5),
            "prio": int(exit_match.group(7)),
        }

    wakeup_match = wakeup_pattern.match(line)
    if wakeup_match:
        return {
            "type": "sched_wakeup",
            "timestamp": float(wakeup_match.group(4)),
            "cpu": int(wakeup_match.group(3)),
            "comm": wakeup_match.group(5),
            "pid": int(wakeup_match.group(6)),
            "target_cpu": int(wakeup_match.group(7)),
        }

    return None

# Function to extract the number of CPUs from the file
def extract_cpu_count(line):
    cpu_pattern = re.compile(r'cpus=(\d+)')
    cpu_match = cpu_pattern.match(line)
    if cpu_match:
        return int(cpu_match.group(1))
    return None

# Function to read the input file and parse it
def parse_file(filename, first_pid=-1):
    parsed_data = []
    exec_pids = set()
    pid_to_cpu = {}  # Map pid to last seen CPU
    first_timestamp = -1
    last_timestamp = 0
    nb_of_cpus = 0
    cpu_usage = {}  # Track last known CPU for each PID
    line_nbr = 0
    
    # Generate a list of colors
    colors = list(mcolors.TABLEAU_COLORS.values())
    
    if first_pid > 0: 
        print(first_pid)
        exec_pids.add(int(first_pid))
    
    with open(filename, 'r') as file:
        for line in file:
            line_nbr += 1
            line = line.strip()
            if line:
                if line.startswith('cpus='):
                    nb_of_cpus = extract_cpu_count(line)
                    continue
                parsed_line = parse_line(line)
                if parsed_line:
                    last_timestamp = parsed_line["timestamp"] - first_timestamp
                    if first_timestamp < 0:
                        first_timestamp = parsed_line["timestamp"]
                    if parsed_line["type"] == "sched_process_exec":
                        exec_pids.add(parsed_line["pid"])
                        parsed_data.append({
                            "type": "sched_process_exec",
                            "timestamp": (parsed_line["timestamp"] - first_timestamp),
                            "cpu": parsed_line["cpu"],
                            "pid": parsed_line["pid"],
                        })
                    elif parsed_line["type"] == "sched_process_fork":
                        if parsed_line["pid"] in exec_pids:
                            exec_pids.add(parsed_line["child_pid"])
                            if parsed_line["pid"] in cpu_usage:
                                cpu_usage[parsed_line["child_pid"]] = cpu_usage[parsed_line["pid"]]
                            else:
                                cpu_usage[parsed_line["child_pid"]] = -1
                        if parsed_line["pid"] in exec_pids or parsed_line["child_pid"] in exec_pids:
                            parsed_data.append({
                            "type": "sched_process_fork",
                            "timestamp": (parsed_line["timestamp"] - first_timestamp),
                            "cpu": parsed_line["cpu"],
                            "pid": parsed_line["child_pid"],
                        })
                    elif parsed_line["type"] == "sched_migrate_task" and parsed_line["pid"] in exec_pids:
                        cpu_usage[parsed_line["pid"]] = parsed_line["cpu"]
                        parsed_data.append({
                            "type": "sched_migrate_task",
                            "timestamp": (parsed_line["timestamp"]-first_timestamp),
                            "cpu": parsed_line["cpu"],
                            "pid": parsed_line["pid"],
                        })
                    elif parsed_line["type"] == "sched_switch" and (parsed_line["prev_pid"] in exec_pids or parsed_line["next_pid"] in exec_pids):
                        cpu_usage[parsed_line["next_pid"]] = parsed_line["cpu"] ######This could be wrong
                        parsed_data.append({
                            "type": "sched_switch",
                            "timestamp": (parsed_line["timestamp"]-first_timestamp),
                            "cpu": parsed_line["cpu"],
                            "prev_pid": parsed_line["prev_pid"],
                            "next_pid": parsed_line["next_pid"],
                        })
                    elif parsed_line["type"] == "sched_wakeup" and (parsed_line["pid"] in exec_pids):
                        cpu_usage[parsed_line["pid"]] = parsed_line["target_cpu"] ######This could be wrong
                        parsed_data.append({
                            "type": "sched_wakeup",
                            "timestamp": (parsed_line["timestamp"]-first_timestamp),
                            "cpu": parsed_line["cpu"],
                            "pid": parsed_line["pid"],
                        })        
                    elif parsed_line["type"] == "sched_process_exit" and parsed_line["pid"] in exec_pids:
                        parsed_data.append({
                            "type": "sched_process_exit",
                            "timestamp": (parsed_line["timestamp"]-first_timestamp),
                            "pid": parsed_line["pid"],
                        })      
     

    # Prepare data for plotting
    threads: Dict[int, Thread] = {}  # Dictionary to store Thread objects by pid
    if first_pid > 0: threads[int(first_pid)] = Thread(int(first_pid), 0, 0)
    
    for entry in parsed_data:
        # Check if the thread already exists
        if (entry["type"] == "sched_process_exec" or entry["type"] == "sched_process_fork") and entry["pid"] not in threads:
            new_thread = Thread(entry["pid"], entry["cpu"], entry["timestamp"])
            new_thread.switch_back(entry["timestamp"])
            threads[entry["pid"]] = new_thread

        if entry["type"] == "sched_migrate_task":
            if entry["pid"] in threads:
                threads[entry["pid"]].migrate(entry["timestamp"] , entry["cpu"])

        elif entry["type"] == "sched_process_exit":
            threads[entry["pid"]].terminate(entry["timestamp"])
        elif entry["type"] == "sched_wakup":
            if entry["pid"] in threads:
                threads[entry["pid"]].switch_back(entry["timestamp"])           
        elif entry["type"] == "sched_switch":
            if entry["prev_pid"] in threads:
                threads[entry["prev_pid"]].switch_away(entry["timestamp"])
            if entry["next_pid"] in threads:
                threads[entry["next_pid"]].switch_back(entry["timestamp"])      
                

    return threads, last_timestamp, nb_of_cpus

colors = ['red', 'blue', 'green', 'yellow', 'purple', 'orange', 'cyan', 'magenta']
# Function to plot and save the graph
def plot_and_save_graph(threads, last_timestamp, filename, nb_cpus):
    fig = make_subplots(rows=1, cols=1)
    pid_legend_added = set()

    # Plot each rectangle
    for idx, (pid, thread) in enumerate(threads.items()):
        prev_timestamp = thread.creation_timestamp
        color = f'rgba({idx * 50 % 255},{idx * 30 % 255},{idx * 100 % 255},0.6)'  # Cycle through colors
        num_events = len(thread.events)
        show_legend = True
        pid_legend_added.add(pid)

        # Use a legendgroup to group traces by PID
        legend_group = f"Thread {pid}"

        if not thread.events:  # If there are no events, only plot switches
            for switch in thread.switches:
                fig.add_trace(go.Scatter(
                    x=[switch[0], switch[1], switch[1], switch[0], switch[0]],
                    y=[thread.cpu - 0.4, thread.cpu - 0.4, thread.cpu + 0.4, thread.cpu + 0.4, thread.cpu - 0.4],
                    fill='toself',
                    fillcolor=color,
                    line=dict(color='rgba(0,0,0,0)'),
                    showlegend=show_legend,
                    legendgroup=legend_group,  # Group traces by PID
                    hoverinfo='x+y',
                    name=f'Thread {pid}'
                ))
                show_legend = False
        else:
            for i, event in enumerate(thread.events):
                switches_in_event = [switch for switch in thread.switches if switch[0] > prev_timestamp and switch[0] < event[0]]
                is_last_event = (i == num_events - 1)

                for switch in switches_in_event:
                    fig.add_trace(go.Scatter(
                        x=[switch[0], switch[1], switch[1], switch[0], switch[0]],
                        y=[event[1] - 0.4, event[1] - 0.4, event[1] + 0.4, event[1] + 0.4, event[1] - 0.4],
                        fill='toself',
                        fillcolor=color,
                        line=dict(color='rgba(0,0,0,0)'),
                        showlegend=show_legend,
                        legendgroup=legend_group,  # Group traces by PID
                        hoverinfo='x+y',
                        name=f'Thread {pid}'
                    ))
                    prev_timestamp = event[0]
                    show_legend = False

                if is_last_event:
                    switches_in_event = [switch for switch in thread.switches if switch[0] > prev_timestamp and switch[0] < last_timestamp]
                    for switch in switches_in_event:
                        fig.add_trace(go.Scatter(
                            x=[switch[0], switch[1], switch[1], switch[0], switch[0]],
                            y=[event[2] - 0.4, event[2] - 0.4, event[2] + 0.4, event[2] + 0.4, event[2] - 0.4],
                            fill='toself',  # Fill the rectangle
                            mode='lines',  # Draw lines between the points
                            fillcolor=color,  # Set the color of the fill
                            line=dict(color='rgba(0,0,0,0)'),  # Hide the outline
                            showlegend=show_legend,
                            legendgroup=legend_group,  # Group traces by PID
                            name=f'Thread {pid}',
                            hoverinfo='x+y'
                        ))
                    show_legend = False    

    # Update layout
    fig.update_layout(
        title="Thread Scheduling Over Time",
        xaxis_title="Time",
        yaxis_title="CPU",
        yaxis=dict(tickmode='linear', tick0=0, dtick=1, range=[-1, nb_cpus]),  # Ensure the y-axis covers all CPUs
        xaxis=dict(range=[0, last_timestamp + 1]),
        bargap=0.2,
        hovermode="closest"
    )

    # Save the figure as an interactive HTML file
    fig.write_html(filename)