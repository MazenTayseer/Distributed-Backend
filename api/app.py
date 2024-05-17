import os
import paramiko
import json
import re

from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

UPLOAD_FOLDER = "/tmp/uploads"

MASTER_NODE_HOST = "master001"
NODE001_NODE_HOST = "node001"

NODE_PORT = 22
NODE_USERNAME = "mazen"
NODE_PASSWORD = "MazenAzure2002"

VMS = [MASTER_NODE_HOST, NODE001_NODE_HOST]

REMOTE_PATH_TEST_CASES = "/home/mazen/gui/uploads"
REMOTE_PATH = "/home/mazen/gui"

os.makedirs(UPLOAD_FOLDER, exist_ok=True)


def upload_to_node(local_path, remote_path, host):
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(host, NODE_PORT, NODE_USERNAME, NODE_PASSWORD)

    # SCPCLient takes a paramiko transport as its only argument
    scp = paramiko.SFTPClient.from_transport(ssh.get_transport())
    scp.put(local_path, remote_path)

    scp.close()
    ssh.close()


def process_images():
    # Command to execute
    command = "mpirun -np 4 -machinefile /home/mazen/gui/machinefile python3 /home/mazen/gui/run.py"

    # Establish SSH connection
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(MASTER_NODE_HOST, NODE_PORT, NODE_USERNAME, NODE_PASSWORD)

    # Execute the command on the remote VM
    stdin, stdout, stderr = ssh.exec_command(command)

    output = stdout.read().decode()
    error = stderr.read().decode()

    # Close the SSH connection
    ssh.close()

    # Create JSON response
    response = {"output": output, "error": error}
    response_sucess = {"output": output}

    return response


def get_images_and_preds(output):
    preimage_pattern = re.compile(r"preimg:(\w+\.\w+)")
    image_pattern = re.compile(r"image:(\w+\.\w+)")
    pred_pattern = re.compile(r"pred:(\w+\.\w+)-(\w+) \(([\d.]+)\)")
    node_pattern = re.compile(r"^node:.*", re.MULTILINE)

    print(output)

    # Extracting images and predictions
    images = image_pattern.findall(output)
    preimages = preimage_pattern.findall(output)
    predictions = pred_pattern.findall(output)
    machine_logs = node_pattern.findall(output)

    # Organizing predictions by image name

    image_predictions = {}
    for image_name in preimages:
        image_predictions[image_name] = []

    for image_name, pred, conf in predictions:
        image_predictions[image_name].append((pred, float(conf)))

    machine_logs = [log.replace("node:", "") for log in machine_logs]

    return preimages, images, image_predictions, machine_logs


@app.route("/upload", methods=["POST"])
def upload_images():
    images = request.files.getlist("images")
    operations = request.form.getlist("operations")

    if len(images) != len(operations):
        return jsonify({"error": "No images uploaded."}), 400

    image_data = []
    for image, op in zip(images, operations):
        local_path = os.path.join(UPLOAD_FOLDER, image.filename)
        image.save(local_path)

        image_info = {"operation": op, "file_path": local_path}
        image_data.append(image_info)

        remote_path = os.path.join(REMOTE_PATH_TEST_CASES, image.filename)
        for host in VMS:
            upload_to_node(local_path, remote_path, host)

    json_local_path = "image_data.json"
    with open(json_local_path, "w") as json_file:
        json.dump(image_data, json_file, indent=4)

    remote_path = os.path.join(REMOTE_PATH, json_local_path)
    for host in VMS:
        upload_to_node(json_local_path, remote_path, host)

    for image in images:
        os.remove(os.path.join(UPLOAD_FOLDER, image.filename))
    os.remove(json_local_path)

    vms_response = process_images()
    output = vms_response["output"]

    preimages, images, image_predictions, machine_logs = get_images_and_preds(output)
    error_logs = vms_response["error"].split("\n")

    if len(error_logs) > 0 and not (len(error_logs) == 1 and error_logs[0] == ""):
        machine_logs.extend(error_logs)

    return (
        jsonify(
            {
                "message": "Successful Processing",
                "Virtual Machines Output": vms_response,
                "preimages": preimages,
                "images": images,
                "predictions": image_predictions,
                "machine_logs": machine_logs,
            }
        ),
        200,
    )


@app.route("/results/<path:filename>")
def static_results(filename):
    return send_from_directory("static/results", filename)


@app.route("/delete/<path:filename>", methods=["DELETE"])
def delete_file(filename):
    file_path = os.path.join("static/results", filename)
    if os.path.exists(file_path):
        os.remove(file_path)
        return jsonify({"message": f"File '{filename}' deleted successfully."}), 200
    return jsonify({"error": f"File '{filename}' not found."}), 404


@app.route("/delete_files_from_nodes/<path:host>", methods=["DELETE"])
def delete_files_from_nodes(host):
    # Establish SSH connection
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(host, NODE_PORT, NODE_USERNAME, NODE_PASSWORD)

    try:
        # Delete files from remote VMs
        command_1 = f"rm -rf {REMOTE_PATH_TEST_CASES}/*"
        stdin, stdout, stderr = ssh.exec_command(command_1)
        # Wait for the command to complete
        stdout.channel.recv_exit_status()

        # Second command
        command_2 = "rm -rf /home/mazen/gui/image_data.json"
        stdin, stdout, stderr = ssh.exec_command(command_2)
        # Wait for the command to complete
        stdout.channel.recv_exit_status()

        command_3 = "rm -rf /home/mazen/gui/results/*"
        stdin, stdout, stderr = ssh.exec_command(command_3)
        # Wait for the command to complete
        stdout.channel.recv_exit_status()

        return jsonify({"message": "Commands executed successfully."}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        # Close the SSH connection
        ssh.close()


@app.route("/check_ssh/<host>")
def check_connection(host):
    try:
        # Establish SSH connection
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(
            host, 22, "mazen", "MazenAzure2002", timeout=10
        )  # Adding timeout for connection attempt

        stdin, stdout, stderr = ssh.exec_command('echo "Successful"')

        response = stdout.read().decode().strip()

        ssh.close()

        return {"message": response}, 200
    except Exception as e:
        return {"message": "Failed to connect"}, 200


@app.route("/upload_test", methods=["POST"])
def upload_test():
    images = ["cat.jpg", "dog.jpg"]

    return (
        jsonify({"message": "Successful Processing", "images": images}),
        200,
    )


@app.route("/esrgan", methods=["GET"])
def try_mpi():
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(
        "master001", 22, "mazen", "MazenAzure2002", timeout=10
    )  # Adding timeout for connection attempt

    stdin, stdout, stderr = ssh.exec_command(
        "mpirun -np 2 -machinefile /home/mazen/gui/machinefile python3 /home/mazen/gui/run.py"
    )

    response = stdout.read().decode().strip()

    ssh.close()

    return {"message": response}, 200


@app.route("/ping")
def ping():
    return (jsonify({"message": "pong"}), 200)


@app.route("/")
def index():
    return (jsonify({"message": "Hello"}), 200)


# app.run(host="0.0.0.0", port=80, debug=True)
# app.run(debug=False)
