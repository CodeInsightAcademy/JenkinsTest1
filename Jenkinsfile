pipeline {
    agent any

    environment {
        APP_URL = "http://localhost:5000"
        APP_PORT = '5000'
        VENV_DIR = 'venv'
        ZAP_REPORT_PATH = "${WORKSPACE}/zap_report.html"
        
        DEPENDENCY_CHECK_REPORT_PATH = "${WORKSPACE}/dependency-check-report.html"
        BANDIT_REPORT_PATH = "${WORKSPACE}/bandit_report.json"
        ZAP_VERSION = "2.14.0" // Specify the ZAP version to download
        ZAP_BASE_DIR = "zap" // Directory to store ZAP
        ZAP_INSTALL_DIR = "${ZAP_BASE_DIR}/ZAP_${ZAP_VERSION}" // Full path to ZAP installation
        ZAP_DOWNLOAD_URL = "https://github.com/zaproxy/zaproxy/releases/download/v${ZAP_VERSION}/ZAP_${ZAP_VERSION}_Linux.tar.gz"
        ZAP_TAR_GZ = "${ZAP_BASE_DIR}/ZAP_${ZAP_VERSION}_Linux.tar.gz"
        ZAP_HOME = "${WORKSPACE}/${ZAP_INSTALL_DIR}" // Where ZAP will be extracted
    }

    stages {
        stage('Checkout Code') {
            steps {
                git url: 'git@github.com:CodeInsightAcademy/JenkinsTest1.git', branch: 'main'
            }
        }

        stage('Setup Environment') {
            steps {
                sh 'python3 -m venv venv'
                sh '. venv/bin/activate && pip install -r requirements.txt'
            }
        }

        stage('Install Dependencies') {
            steps {
                sh '''
                    python3 -m venv venv
                    . venv/bin/activate
                    pip install -r requirements.txt
                '''
            }
        }

        stage('Run Tests') {
            steps {
                sh '''#!/bin/bash
                source venv/bin/activate
                pytest
                '''
            }
        }

        stage('Deploy App Locally') {
            steps {
                sh '''
                    pkill -f "gunicorn" || true
                '''
                sh '''
                    . ${VENV_DIR}/bin/activate
                    nohup gunicorn --bind 0.0.0.0:5000 app:app > app.log 2>&1 &
                '''
            }
        }
        // stage('SCA Scan (Dependency-Check)') {
        //     steps {
        //         sh '''
        //         /opt/dependency-check/bin/dependency-check.sh \
        //         --scan . \
        //         --format HTML \
        //         --project MovieRecommender \
        //         --out . \
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
                sh '''#!/bin/bash
                source venv/bin/activate
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
                // Kill gunicorn and start Flask development server for DAST scan
                sh '''
                    pkill -f gunicorn || true
                    . venv/bin/activate
                    nohup python3 app.py &
                    sleep 10
                    curl --fail ${APP_URL}
                    echo "App is running for DAST scan!"
                '''
            }
            // IMPORTANT: No post cleanup for the app here, as it's needed for the next DAST stage.
            // Cleanup will happen in the DAST Scan stage's post block.
        }

        stage('DAST Scan (OWASP ZAP)') {
            steps {
                echo "Starting DAST Scan on ${APP_URL}"

                // --- ZAP Installation (download and extract if not present) ---
                script {
                    sh "mkdir -p ${env.ZAP_BASE_DIR}"
                    if (!fileExists("${env.ZAP_HOME}/zap.sh")) {
                        echo "Downloading and extracting OWASP ZAP ${env.ZAP_VERSION}..."
                        sh "wget -q ${env.ZAP_DOWNLOAD_URL} -O ${env.ZAP_TAR_GZ}"
                        sh "tar -xzf ${env.ZAP_TAR_GZ} -C ${env.ZAP_BASE_DIR}"
                        sh "rm ${env.ZAP_TAR_GZ}" // Clean up the tarball
                    } else {
                        echo "OWASP ZAP ${env.ZAP_VERSION} already extracted."
                    }
                }

                // --- Install zap-cli into the virtual environment ---
                // zap-cli is a Python client for ZAP's API, making scripting easier.
                sh '. venv/bin/activate && pip install zap-cli'

                // --- Start ZAP in Daemon Mode ---
                sh '''
                    echo "Starting ZAP daemon..."
                    # -daemon: Runs ZAP in the background
                    # -port 8080: ZAP's API port
                    # -host 0.0.0.0: Listens on all interfaces
                    # -config api.disablekey=true: Disables API key requirement for simplicity in CI (NOT recommended for production)
                    nohup ${ZAP_HOME}/zap.sh -daemon -port 8080 -host 0.0.0.0 -config api.disablekey=true &
                '''

                // --- Wait for ZAP daemon to start and be ready ---
                script {
                    def zapReady = false
                    timeout(time: 2, unit: 'MINUTES') { // Max 2 minutes wait
                        while (!zapReady) {
                            try {
                                sh "curl -sI http://localhost:8080" // Check ZAP API endpoint
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
                sh '''
                    . venv/bin/activate
                    echo "Running ZAP active scan on ${APP_URL}..."
                    # --recursive: Follows links recursively
                    # zap-cli will exit with non-zero if issues found based on its default policies, failing the stage.
                    zap-cli --zap-path ${ZAP_HOME} --port 8080 active-scan --recursive ${APP_URL}
                '''

                // --- Generate HTML Report ---
                sh '''
                    . venv/bin/activate
                    echo "Generating ZAP HTML report..."
                    mkdir -p target/zap-reports
                    zap-cli --zap-path ${ZAP_HOME} --port 8080 report --output target/zap-reports/zap-report.html --format html
                '''
            }
            post {
                always {
                    script {
                        // --- Shutdown ZAP Daemon ---
                        echo "Shutting down ZAP daemon..."
                        sh "pkill -f 'zap.sh' || true" // More robust way to kill ZAP processes
                        sleep 5 // Give ZAP a moment to shut down cleanly

                        // --- Kill the Flask App (started in 'Deploy App for DAST' stage) ---
                        def appPidsOutput = sh(script: 'lsof -t -i :5000', returnStdout: true).trim()
                        def appPids = appPidsOutput.replaceAll('\\\\n', ' ')

                        if (appPids) {
                            echo "Killing Flask app process(es) on port 5000: ${appPids}"
                            sh "kill ${appPids}"
                        } else {
                            echo "No Flask app process found on port 5000 to kill."
                        }
                    }
                    archiveArtifacts artifacts: 'target/zap-reports/**/*.html', allowEmptyArchive: true
                    echo "ZAP DAST scan completed and application cleaned up."
                }
                failure {
                    // This block executes if the 'steps' in this stage (e.g., zap-cli active-scan) fail.
                    // By default, zap-cli will exit with a non-zero code if it finds issues, triggering this.
                    echo "ZAP DAST scan detected vulnerabilities or failed to complete successfully!"
                    // You can add more detailed report analysis here if needed,
                    // e.g., to fail only on specific severity levels.
                    // sh ". venv/bin/activate && python YOUR_SCRIPT_TO_ANALYZE_ZAP_REPORT.py target/zap-reports/zap-report.html"
                }
            }
        }

        stage('Cleanup') {
            steps {
                echo "Cleaning up virtual environment..."
                sh 'rm -rf venv'
                echo "Cleaning up ZAP installation directory..."
                sh "rm -rf ${env.ZAP_BASE_DIR}"
            }
        }
    }
}
