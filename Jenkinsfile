pipeline {
    agent any

    environment {
        APP_URL = "http://localhost:5000"
        APP_PORT = '5000'
        VENV_DIR = 'venv' // Centralized virtual environment directory name

        // ZAP specific environment variables
        ZAP_VERSION = "2.14.0" // Specify the ZAP version to download. Consider upgrading to "2.16.1"
        ZAP_BASE_DIR = "zap" // Directory to store ZAP download and extraction
        ZAP_INSTALL_DIR = "${ZAP_BASE_DIR}/ZAP_${ZAP_VERSION}" // Full path to ZAP installation
        
        // *******************************************************************
        // IMPORTANT: Copy this line EXACTLY. No [ ] or ( ) around the URL.
        // *******************************************************************
        ZAP_DOWNLOAD_URL = "https://github.com/zaproxy/zap-archive/releases/download/zap-v${ZAP_VERSION}/ZAP_${ZAP_VERSION}_Linux.tar.gz"
        // If you switch to ZAP_VERSION = "2.16.1", use this instead:
        // ZAP_DOWNLOAD_URL = "https://github.com/zaproxy/zaproxy/releases/download/v${ZAP_VERSION}/ZAP_${ZAP_VERSION}_Linux.tar.gz"
        ZAP_TAR_GZ = "${ZAP_BASE_DIR}/ZAP_${ZAP_VERSION}_Linux.tar.gz"
        ZAP_HOME = "${WORKSPACE}/${ZAP_INSTALL_DIR}" // Where ZAP will be extracted
    }

    stages {
        stage('Declarative: Checkout SCM') {
            steps {
                checkout scm
            }
        }

        stage('Checkout Code') {
            steps {
                git url: 'git@github.com:CodeInsightAcademy/JenkinsTest1.git', branch: 'main'
            }
        }

        stage('Install Dependencies') {
            steps {
                echo "Setting up Python virtual environment and installing dependencies..."
                sh "python3 -m venv ${env.VENV_DIR}"
                sh ". ${env.VENV_DIR}/bin/activate && pip install -r requirements.txt"
            }
        }

        stage('Run Tests') {
            steps {
                echo "Running application tests..."
                sh ". ${env.VENV_DIR}/bin/activate && pytest"
            }
        }

        stage('Deploy App Locally') {
            steps {
                echo "Killing existing gunicorn processes (if any)..."
                sh "pkill -f \"gunicorn\" || true"
                echo "Starting application locally with gunicorn..."
                sh "nohup . ${env.VENV_DIR}/bin/activate && gunicorn --bind 0.0.0.0:${env.APP_PORT} app:app > app.log 2>&1 &"
            }
        }

        stage('Unit Tests') {
            steps {
                echo "Running unit tests again..."
                sh ". ${env.VENV_DIR}/bin/activate && pytest"
            }
            post {
                failure {
                    echo 'Unit tests failed!'
                }
            }
        }

        stage('Deploy App for DAST') {
            steps {
                echo "Ensuring no gunicorn and starting Flask dev server for DAST scan..."
                sh "pkill -f gunicorn || true"
                sh "nohup python3 app.py &"
                echo "Waiting 10 seconds for Flask app to start..."
                sleep 10
                echo "Verifying Flask app is running at ${APP_URL}..."
                sh "curl --fail ${APP_URL}"
                echo "App is running for DAST scan!"
            }
        }

        stage('DAST Scan (OWASP ZAP)') {
            steps {
                echo "Starting DAST Scan on ${APP_URL}"

                // --- ZAP Installation (download and extract if not present) ---
                script {
                    sh "mkdir -p ${env.ZAP_BASE_DIR}"
                    if (!fileExists("${env.ZAP_HOME}/zap.sh")) {
                        echo "Downloading and extracting OWASP ZAP ${env.ZAP_VERSION}..."
                        sh "wget --no-verbose ${env.ZAP_DOWNLOAD_URL} -O ${env.ZAP_TAR_GZ}"
                        sh "tar -xzf ${env.ZAP_TAR_GZ} -C ${env.ZAP_BASE_DIR}"
                        sh "rm ${env.ZAP_TAR_GZ}"
                    } else {
                        echo "OWASP ZAP ${env.ZAP_VERSION} already extracted."
                    }
                }

                // --- Install zap-cli into the virtual environment ---
                script {
                    echo "Checking connectivity to PyPI for zap-cli (via curl for diagnostics)..."
                    sh "curl -v --max-time 30 https://pypi.org/simple/zap-cli/"
                    
                    echo "Attempting to install a common package (requests) to test general PyPI access..."
                    sh ". ${env.VENV_DIR}/bin/activate && pip install --no-cache-dir --index-url https://pypi.org/simple/ --verbose requests"
                    
                    echo "Attempting to install zap-cli..."
                    sh ". ${env.VENV_DIR}/bin/activate && pip install --no-cache-dir --index-url https://pypi.org/simple/ --verbose zap-cli"
                }

                // --- Start ZAP in Daemon Mode ---
                echo "Starting ZAP daemon..."
                sh "nohup ${env.ZAP_HOME}/zap.sh -daemon -port 8080 -host 0.0.0.0 -config api.disablekey=true > zap_daemon.log 2>&1 &"

                // --- Wait for ZAP daemon to start and be ready ---
                script {
                    def zapReady = false
                    timeout(time: 2, unit: 'MINUTES') {
                        while (!zapReady) {
                            try {
                                echo "Checking ZAP API endpoint (http://localhost:8080/JSON/core/view/version/)..."
                                sh "curl --fail --silent http://localhost:8080/JSON/core/view/version/"
                                zapReady = true
                                echo "ZAP daemon is ready."
                            } catch (e) {
                                echo "Waiting for ZAP daemon to start (checking every 10s)..."
                                sleep 10
                            }
                        }
                    }
                }

                // --- Run ZAP Active Scan using zap-cli ---
                echo "Running ZAP active scan on ${APP_URL}..."
                sh ". ${env.VENV_DIR}/bin/activate && zap-cli --zap-path ${env.ZAP_HOME} --port 8080 active-scan --recursive ${env.APP_URL}"

                // --- Generate HTML Report ---
                echo "Generating ZAP HTML report..."
                sh "mkdir -p target/zap-reports && . ${env.VENV_DIR}/bin/activate && zap-cli --zap-path ${env.ZAP_HOME} --port 8080 report --output target/zap-reports/zap-report.html --format html"
            }
            post {
                always {
                    script {
                        echo "Shutting down ZAP daemon..."
                        sh "pkill -f 'zap.sh' || true"
                        sleep 5

                        echo "Killing Flask app processes on port ${env.APP_PORT}..."
                        def appPidsOutput = sh(script: "lsof -t -i :${env.APP_PORT}", returnStdout: true).trim().replaceAll('\r', '')
                        def appPidsList = appPidsOutput.split('\\s+').findAll { it.trim() != "" }

                        if (appPidsList) {
                            echo "Found PIDs: ${appPidsList.join(' ')}"
                            for (pid in appPidsList) {
                                if (pid.isInteger()) {
                                    sh "kill ${pid} || true"
                                } else {
                                    echo "Warning: '${pid}' is not a valid PID. Skipping."
                                }
                            }
                        } else {
                            echo "No Flask app process found on port ${env.APP_PORT} to kill."
                        }
                    }
                    archiveArtifacts artifacts: 'target/zap-reports/**/*.html', allowEmptyArchive: true
                    echo "ZAP DAST scan completed and application cleaned up."
                }
                failure {
                    echo "ZAP DAST scan detected vulnerabilities or failed to complete successfully!"
                }
            }
        }

        stage('Cleanup') {
            steps {
                echo "Cleaning up virtual environment..."
                sh "rm -rf ${env.VENV_DIR}"
                echo "Cleaning up ZAP installation directory..."
                sh "rm -rf ${env.ZAP_BASE_DIR}"
            }
        }
    }
}
