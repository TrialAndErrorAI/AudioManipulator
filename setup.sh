#!/bin/bash

export_env_vars() {
 export OTEL_RESOURCE_ATTRIBUTES=service.name=AudioManipulator
 export OTEL_EXPORTER_OTLP_ENDPOINT=http://174.138.34.94:4317 
 export OTEL_EXPORTER_OTLP_PROTOCOL=grpc   
}

# Function to create or activate a virtual environment
prepare_install() {
    if [ -d ".venv" ]; then
        echo "Venv found. This implies Audio Manipulator already has a virtual environment"
        
        . .venv/bin/activate

    else
        echo "Creating venv..."
        requirements_file="requirements.txt"
        echo "Checking if python exists"
        if command -v python3.10 > /dev/null 2>&1; then
            py=$(which python3.10)
            echo "Using python3.10"
        else
            if python --version | grep -qE "3\.(7|8|9|10)\."; then
                py=$(which python)
                echo "Using python"
            else
                echo "Please install Python3 or 3.10 manually."
                exit 1
            fi
        fi

        $py -m venv .venv
        . .venv/bin/activate
        python -m ensurepip
        # Update pip within the virtual environment
        pip3 install --upgrade pip
        echo "Installing Audio Manipulator dependencies..."
        python -m pip install -r requirements.txt
        install_open_telemetry
        finish
    fi
}

# Function to finish installation (this should install missing dependencies)
finish() {
    # Check if required packages are installed and install them if not
    if [ -f "${requirements_file}" ]; then
        installed_packages=$(python -m pip freeze)
        while IFS= read -r package; do
            expr "${package}" : "^#.*" > /dev/null && continue
            package_name=$(echo "${package}" | sed 's/[<>=!].*//')
            if ! echo "${installed_packages}" | grep -q "${package_name}"; then
                echo "${package_name} not found. Attempting to install..."
                python -m pip install --upgrade "${package}"
            fi
        done < "${requirements_file}"
    else
        echo "${requirements_file} not found. Please ensure the requirements file with required packages exists."
    fi
}

# Function to install open telemetry bootstrap
install_open_telemetry() {
    echo "Installing Open Telemetry Bootstrap..."
    opentelemetry-bootstrap --action=install
    echo "Open Telemetry Bootstrap installed."
}

# Function to run the Audio Manipulator application

start_audio_manipulator() {
    opentelemetry-instrument gunicorn -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000 main:app --timeout 300
}

# ------------------------------------------------ #
#              Main function                       #
# ------------------------------------------------ #

export_env_vars
prepare_install
start_audio_manipulator

    
