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
        
        // ZAP_VERSION = "2.14.0" // Or update to "2.16.1" as discussed for latest
        // ZAP_BASE_DIR = "zap"
        // ZAP_INSTALL_DIR = "${ZAP_BASE_DIR}/ZAP_${ZAP_VERSION}"
        // IMPORTANT: Use the correct ZAP_DOWNLOAD_URL that worked manually
        ZAP_DOWNLOAD_URL = "https://github.com/zaproxy/zap-archive/releases/download/zap-v${ZAP_VERSION}/ZAP_${ZAP_VERSION}_Linux.tar.gz" // This URL worked for v2.14.0
        // If you switch to ZAP_VERSION = "2.16.1", use:
        // ZAP_DOWNLOAD_URL = "https://github.com/zaproxy/zaproxy/releases/download/v${ZAP_VERSION}/ZAP_${ZAP_VERSION}_Linux.tar.gz"
        ZAP_TAR_GZ = "${ZAP_BASE_DIR}/ZAP_${ZAP_VERSION}_Linux.tar.gz"
        ZAP_HOME = "${WORKSPACE}/${ZAP_INSTALL_DIR}"
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

      stage('DAST Scan (OWASP ZAP)') {
            steps {
                echo "Starting DAST Scan on ${APP_URL}"

                // --- ZAP Installation (download and extract if not present) ---
                script {
                    sh '''
                        # Removed #!/bin/bash and -o pipefail for compatibility
                        set -eux
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
                sh '. venv/bin/activate && pip install zap-cli'

                // --- Start ZAP in Daemon Mode ---
                script { // Added script block for better Groovy variable access
                    sh '''
                        # Removed #!/bin/bash and -o pipefail for compatibility
                        set -eux
                        echo "Starting ZAP daemon..."
                        nohup ${ZAP_HOME}/zap.sh -daemon -port 8080 -host 0.0.0.0 -config api.disablekey=true &
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
                script { // Added script block
                    sh '''
                        # Removed #!/bin/bash and -o pipefail for compatibility
                        set -eux
                        . venv/bin/activate
                        echo "Running ZAP active scan on ${APP_URL}..."
                        zap-cli --zap-path ${ZAP_HOME} --port 8080 active-scan --recursive ${APP_URL}
                    '''
                }

                // --- Generate HTML Report ---
                script { // Added script block
                    sh '''
                        # Removed #!/bin/bash and -o pipefail for compatibility
                        set -eux
                        . venv/bin/activate
                        echo "Generating ZAP HTML report..."
                        mkdir -p target/zap-reports
                        zap-cli --zap-path ${ZAP_HOME} --port 8080 report --output target/zap-reports/zap-report.html --format html
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
                        // Ensure lsof output is clean
                        def appPidsOutput = sh(script: 'lsof -t -i :5000', returnStdout: true).trim().replaceAll('\r', '')
                        def appPidsList = appPidsOutput.split('\\s+').findAll { it.trim() != "" } // Split and filter empty strings

                        if (appPidsList) {
                            echo "Killing Flask app process(es) on port 5000: ${appPidsList.join(' ')}"
                            for (pid in appPidsList) {
                                // Add a check to ensure it's a number and handle potential errors gracefully
                                if (pid.isInteger()) {
                                    sh "kill ${pid} || true" // Use || true to prevent individual kill failure from breaking the loop
                                } else {
                                    echo "Warning: '${pid}' is not a valid PID. Skipping."
                                }
                            }
                        } else {
                            echo "No Flask app process found on port 5000 to kill."
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
                sh 'rm -rf venv'
                echo "Cleaning up ZAP installation directory..."
                sh "rm -rf ${env.ZAP_BASE_DIR}"
            }
        }
    }
}
