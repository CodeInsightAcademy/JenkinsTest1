pipeline {
    agent any

    environment {
        APP_URL = "http://localhost:5000"
        APP_PORT = '5000'
        VENV_DIR = 'venv'
        ZAP_REPORT_PATH = "${WORKSPACE}/zap_report.html"
        
        DEPENDENCY_CHECK_REPORT_PATH = "${WORKSPACE}/dependency-check-report.html"
        BANDIT_REPORT_PATH = "${WORKSPACE}/bandit_report.json"
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
                sh '''
                    . venv/bin/activate
                    nohup python3 app.py &
                    sleep 10
                    curl --fail ${APP_URL} # Use the defined APP_URL here as well
                    echo "App is running for DAST scan!"
                '''
            }
            post {
                always {
                    script {
                        def pidsOutput = sh(script: 'lsof -t -i :5000', returnStdout: true).trim()
                        def pids = pidsOutput.replaceAll('\\n', ' ')

                        if (pids) {
                            echo "Killing process(es) on port 5000: ${pids}"
                            sh "kill ${pids}"
                        } else {
                            echo "No process found on port 5000 to kill."
                        }
                    }
                }
            }
        }

        stage('DAST Scan (OWASP ZAP)') {
            steps {
                echo "Starting DAST Scan on ${APP_URL}"
                // Placeholder for your actual ZAP scan command/step
                // This is where APP_URL would typically be used
                // Example: zapPublisher port: 5000, targetURL: "${APP_URL}", ...
                // For demonstration, just echo success
                sh "echo 'Simulating ZAP scan using ${APP_URL}'"
                // Add your actual ZAP scan command here. It will likely use APP_URL.
                // If you're using a ZAP Jenkins plugin, refer to its documentation for how to pass the target URL.
            }
            post {
                always {
                    archiveArtifacts artifacts: 'target/zap-reports/**/*.html', allowEmptyArchive: true
                    // You might want to evaluate the ZAP report here to determine success/failure
                    // For now, it echoes a failure message as per your log.
                    echo "ZAP DAST scan completed." // Change this to reflect success if no vulnerabilities
                }
                failure {
                    echo "ZAP DAST scan failed or found vulnerabilities!"
                }
            }
        }

        stage('Cleanup') {
            steps {
                echo "Cleaning up..."
                // Add any other cleanup commands here, if necessary
            }
        }
    }
}
