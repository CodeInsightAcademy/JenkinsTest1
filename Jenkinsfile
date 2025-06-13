pipeline {
    agent any

    environment {
        APP_URL = "http://localhost:5000"
        APP_PORT = '5000'
        VENV_DIR = 'venv'
        ZAP_REPORT_PATH = "${WORKSPACE}/zap_report.html" // Unused in current ZAP commands, kept for future use
        DEPENDENCY_CHECK_REPORT_PATH = "${WORKSPACE}/dependency-check-report.html" // Unused (commented stage)
        BANDIT_REPORT_PATH = "${WORKSPACE}/bandit_report.json" // Unused (commented stage)
        ZAP_VERSION = "2.14.0" // Specify the ZAP version to download. Consider upgrading to "2.16.1"
        ZAP_BASE_DIR = "zap" // Directory to store ZAP
        ZAP_INSTALL_DIR = "${ZAP_BASE_DIR}/ZAP_${ZAP_VERSION}" // Full path to ZAP installation
        
        // Correct download URL for ZAP 2.14.0 from the archive
        // If you switch to ZAP_VERSION = "2.16.1", use: "[https://github.com/zaproxy/zaproxy/releases/download/v$](https://github.com/zaproxy/zaproxy/releases/download/v$){ZAP_VERSION}/ZAP_${ZAP_VERSION}_Linux.tar.gz"
        ZAP_DOWNLOAD_URL = "https://github.com/zaproxy/zap-archive/releases/download/zap-v${ZAP_VERSION}/ZAP_${ZAP_VERSION}_Linux.tar.gz"
        ZAP_TAR_GZ = "${ZAP_BASE_DIR}/ZAP_${ZAP_VERSION}_Linux.tar.gz"
        ZAP_HOME = "${WORKSPACE}/${ZAP_INSTALL_DIR}" // Where ZAP will be extracted
    }

    stages {
        stage('Declarative: Checkout SCM') {
            steps {
                // This step typically uses the SCM configuration from the Jenkins job itself.
                checkout scm
            }
        }

        stage('Checkout Code') {
            steps {
                // Explicit checkout for pipeline script
                git url: 'git@github.com:CodeInsightAcademy/JenkinsTest1.git', branch: 'main' // Removed credentialsId if not needed, as Declarative SCM might handle it
            }
        }

        stage('Setup Environment') {
            steps {
                sh "python3 -m venv ${env.VENV_DIR}"
                sh ". ${env.VENV_DIR}/bin/activate && pip install -r requirements.txt"
            }
        }

        stage('Install Dependencies') {
            // This stage seems redundant if "Setup Environment" already installs requirements.
            // Leaving it as is based on your provided structure, but consider consolidating.
            steps {
                sh '''
                    python3 -m venv ''' + env.VENV_DIR + '''
                    . ''' + env.VENV_DIR + '''/bin/activate
                    pip install -r requirements.txt
                '''
            }
        }

        stage('Run Tests') {
            steps {
                sh '''
                    source ''' + env.VENV_DIR + '''/bin/activate
                    pytest
                '''
            }
        }

        stage('Deploy App Locally') {
            steps {
                sh "pkill -f \"gunicorn\" || true" // Ensure previous gunicorn processes are killed
                sh '''
                    . ''' + env.VENV_DIR + '''/bin/activate
                    nohup gunicorn --bind 0.0.0.0:''' + env.APP_PORT + ''' app:app > app.log 2>&1 &
                '''
            }
        }

        // Uncomment the following stages if you want to include SCA and SAST scans
        // stage('SCA Scan (Dependency-Check)') {
        //     steps {
        //         sh '''
        //         /opt/dependency-check/bin/dependency-check.sh \\
        //         --scan . \\
        //         --format HTML \\
        //         --project MovieRecommender \\
        //         --out . \\
        //         --failOnCVSS 8
        //         '''
        //     }
        //     post {
        //         always {
        //             archiveArtifacts artifacts: 'dependency-check-report.html', fingerprint: true
        //         }
        //         failure {
        //             echo 'Dependency-Check scan failed or found vulnerabilities!'
        //         }
        //     }
        // }

        // stage('SAST Scan (Bandit)') {
        //     steps {
        //         sh '. venv/bin/activate && bandit -r . -f json -o bandit_report.json --severity-level medium'
        //     }
        //     post {
        //         always {
        //             archiveArtifacts artifacts: '**/bandit_report.json', fingerprint: true
        //         }
        //         failure {
        //             echo 'Bandit SAST scan failed or found vulnerabilities!'
        //         }
        //     }
        // }

        stage('Unit Tests') {
            steps {
                sh '''
                    source ''' + env.VENV_DIR + '''/bin/activate
                    pytest
                '''
            }
            post {
                failure {
                    echo 'Unit tests failed!'
                }
            }
        }

        stage('Deploy App for DAST') {
            steps {
                // Kill any lingering gunicorn processes and start Flask development server for DAST scan
                sh "pkill -f gunicorn || true"
                sh '''
                    . ''' + env.VENV_DIR + '''/bin/activate
                    nohup python3 app.py &
                    sleep 10
                    curl --fail ''' + env.APP_URL + '''
                    echo "App is running for DAST scan!"
                '''
            }
            // No post cleanup here, as the app is needed for the next DAST stage.
            // Cleanup will happen in the DAST Scan stage's post block.
        }

        stage('DAST Scan (OWASP ZAP)') {
            steps {
                echo "Starting DAST Scan on ${APP_URL}"

                // --- ZAP Installation (download and extract if not present) ---
                script {
                    sh '''
                        set -eux # Removed -o pipefail for wider compatibility
                        mkdir -p ''' + env.ZAP_BASE_DIR + '''
                        if [ ! -f "''' + env.ZAP_HOME + '''/zap.sh" ]; then
                            echo "Downloading and extracting OWASP ZAP ''' + env.ZAP_VERSION + '''..."
                            wget --no-verbose ''' + env.ZAP_DOWNLOAD_URL + ''' -O ''' + env.ZAP_TAR_GZ + '''
                            tar -xzf ''' + env.ZAP_TAR_GZ + ''' -C ''' + env.ZAP_BASE_DIR + '''
                            rm ''' + env.ZAP_TAR_GZ + ''' # Clean up the tarball
                        else
                            echo "OWASP ZAP ''' + env.ZAP_VERSION + ''' already extracted."
                        fi
                    '''
                }

                // --- Install zap-cli into the virtual environment ---
                script {
                    echo "Checking connectivity to PyPI for zap-cli..."
                    // This curl command attempts to fetch the simple index for zap-cli from PyPI.
                    // The -v (verbose) flag will show connection details, redirects, and potential proxy issues.
                    // --max-time 30 will ensure it doesn't hang indefinitely.
                    sh 'curl -v --max-time 30 [https://pypi.org/simple/zap-cli/](https://pypi.org/simple/zap-cli/)'
                    
                    echo "Attempting to install a common package (requests) to test general PyPI access..."
                    // Try installing 'requests' with the same flags to diagnose PyPI access
                    sh '. ' + env.VENV_DIR + '/bin/activate && pip install --no-cache-dir --index-url [https://pypi.org/simple/](https://pypi.org/simple/) --verbose requests'
                    
                    echo "Attempting to install zap-cli..."
                    // Proceed with zap-cli installation after testing with requests
                    sh '. ' + env.VENV_DIR + '/bin/activate && pip install --no-cache-dir --index-url [https://pypi.org/simple/](https://pypi.org/simple/) --verbose zap-cli'
                }

                // --- Start ZAP in Daemon Mode ---
                script {
                    sh '''
                        set -eux # Removed -o pipefail for wider compatibility
                        echo "Starting ZAP daemon..."
                        nohup ''' + env.ZAP_HOME + '''/zap.sh -daemon -port 8080 -host 0.0.0.0 -config api.disablekey=true &
                    '''
                }

                // --- Wait for ZAP daemon to start and be ready ---
                script {
                    def zapReady = false
                    timeout(time: 2, unit: 'MINUTES') { // Max 2 minutes wait
                        while (!zapReady) {
                            try {
                                // Check ZAP API endpoint to ensure ZAP is running
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
                script {
                    sh '''
                        set -eux # Removed -o pipefail for wider compatibility
                        . ''' + env.VENV_DIR + '''/bin/activate
                        echo "Running ZAP active scan on ''' + env.APP_URL + '''..."
                        zap-cli --zap-path ''' + env.ZAP_HOME + ''' --port 8080 active-scan --recursive ''' + env.APP_URL + '''
                    '''
                }

                // --- Generate HTML Report ---
                script {
                    sh '''
                        set -eux # Removed -o pipefail for wider compatibility
                        . ''' + env.VENV_DIR + '''/bin/activate
                        echo "Generating ZAP HTML report..."
                        mkdir -p target/zap-reports
                        zap-cli --zap-path ''' + env.ZAP_HOME + ''' --port 8080 report --output target/zap-reports/zap-report.html --format html
                    '''
                }
            }
            post {
                always {
                    script {
                        // --- Shutdown ZAP Daemon ---
                        echo "Shutting down ZAP daemon..."
                        sh "pkill -f 'zap.sh' || true" // More robust way to kill ZAP processes
                        sleep 5 // Give ZAP a moment to shut down cleanly

                        // --- Kill the Flask App (started in 'Deploy App for DAST' stage) ---
                        // Ensure lsof output is clean and use APP_PORT environment variable
                        def appPidsOutput = sh(script: "lsof -t -i :${env.APP_PORT}", returnStdout: true).trim().replaceAll('\r', '')
                        def appPidsList = appPidsOutput.split('\\s+').findAll { it.trim() != "" } // Split and filter empty strings

                        if (appPidsList) {
                            echo "Killing Flask app process(es) on port ${env.APP_PORT}: ${appPidsList.join(' ')}"
                            for (pid in appPidsList) {
                                // Add a check to ensure it's a number and handle potential errors gracefully
                                if (pid.isInteger()) {
                                    sh "kill ${pid} || true" // Use || true to prevent individual kill failure from breaking the loop
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
                sh 'rm -rf ' + env.VENV_DIR
                echo "Cleaning up ZAP installation directory..."
                sh "rm -rf ${env.ZAP_BASE_DIR}"
            }
        }
    }
}
