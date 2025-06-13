// Jenkinsfile for DevSecOps Pipeline
pipeline {
    agent any

    environment {
        // Define your app's URL for DAST scan
        APP_URL = "http://localhost:5000" // Adjust if your app runs on a different IP/port
        // For ZAP, specify where to store results
        ZAP_REPORT_PATH = "${WORKSPACE}/zap_report.html"
        // For Dependency-Check, specify where to store results
        DEPENDENCY_CHECK_REPORT_PATH = "${WORKSPACE}/dependency-check-report.html"
        // For Bandit, specify where to store results
        BANDIT_REPORT_PATH = "${WORKSPACE}/bandit_report.json"
    }

    stages {
        stage('Checkout Code') {
            steps {
                git url: 'git@github.com:CodeInsightAcademy/JenkinsTest1.git', branch: 'main' // Replace with your actual repo URL
            }
        }

        stage('Setup Environment') {
            steps {
                sh 'python3 -m venv venv'
                sh '. venv/bin/activate && pip install -r requirements.txt'
            }
        }

        stage('SCA Scan (Dependency-Check)') {
                steps {
                    // Run Dependency-Check against the requirements.txt
                    sh """
                    /opt/dependency-check/bin/dependency-check.sh \
                      --nvdApiKey YOUR_NVD_API_KEY \
                      --scan . \
                      --format HTML \
                      --project MovieRecommender \
                      --out dependency-check-report.html \
                      --data .dependency-check-data
                        
                    """
                }
                post {
                    always {
                        archiveArtifacts artifacts: '**/dependency-check-report.html', fingerprint: true
                    }
                    failure {
                        echo 'Dependency-Check scan failed or found vulnerabilities!'
                    }
                }
            }
        stage('SAST Scan (Bandit)') {
            steps {
                sh '. venv/bin/activate && bandit -r . -f json -o "${BANDIT_REPORT_PATH}" --severity-level M'
                // -r . : recursive scan from current directory
                // -f json : output in JSON format
                // -o : output file
                // --severity-level M : report findings with Medium or High severity
            }
            post {
                always {
                    archiveArtifacts artifacts: '**/bandit_report.json', fingerprint: true
                }
                failure {
                    echo 'Bandit SAST scan failed or found vulnerabilities!'
                }
            }
        }

        stage('Unit Tests') {
            steps {
                sh '. venv/bin/activate && pytest test_app.py'
            }
            post {
                failure {
                    echo 'Unit tests failed!'
                }
            }
        }

        stage('Deploy App for DAST') {
            steps {
                // Start the Flask app in the background. You might need a more robust deployment method
                // for production, e.g., Gunicorn or a proper web server.
                sh 'nohup python3 app.py > app.log 2>&1 &'
                // Give the app a moment to start
                sh 'sleep 10'
                // Verify app is running (optional but good practice)
                sh 'curl --fail ${APP_URL} || (echo "App not running!" && exit 1)'
            }
            post {
                always {
                    // Ensure the process is killed even if DAST fails
                    script {
                        def pids = sh(script: "lsof -t -i :5000 || echo ''", returnStdout: true).trim()
                        if (pids) {
                            echo "Killing process on port 5000: ${pids}"
                            sh "kill ${pids}"
                        } else {
                            echo "No process found on port 5000."
                        }
                    }
                }
            }
        }

        stage('DAST Scan (OWASP ZAP)') {
            steps {
                // Ensure ZAP has network access to the app
                // This runs a quick scan, for more comprehensive scans, refer to ZAP documentation.
                sh """
                /opt/owasp-zap/zap.sh -cmd \\
                    -port 8090 -host 127.0.0.1 \\
                    -config api.disablekey=true \\
                    -newsession zap_scan \\
                    -url ${APP_URL} \\
                    -autorun \\
                    -htmlreport ${ZAP_REPORT_PATH}
                """
                // `-cmd`: run in command line mode
                // `-port`/`-host`: ZAP's own port/host
                // `-url`: the target application URL
                // `-autorun`: automatically run passive and active scans
                // `-htmlreport`: output report in HTML format
            }
            post {
                always {
                    archiveArtifacts artifacts: '**/zap_report.html', fingerprint: true
                }
                failure {
                    echo 'ZAP DAST scan failed or found vulnerabilities!'
                }
            }
        }

        stage('Cleanup') {
            steps {
                sh 'rm -rf venv'
            }
        }
    }
}


// pipeline {
//     agent any

//     environment {
//         APP_PORT = '5000'
//         VENV_DIR = 'venv'
//     }

//     stages {
//         stage('Checkout Code') {
//             steps {                    
//                 git url: 'git@github.com:CodeInsightAcademy/JenkinsTest1.git', branch: 'main'
//             }
//         }

//         stage('Install Dependencies') {
//             steps {
//                 sh '''
//                     python3 -m venv venv
//                     . venv/bin/activate
//                     pip install -r requirements.txt
//                 '''
//             }
//         }
//         stage('Run Tests') {
//             steps {
//                 sh '''#!/bin/bash
//                 source venv/bin/activate
//                 pytest
//                 '''
//             }
//         }        

//         stage('Deploy App Locally') {
//             steps {
//                 // Stop any existing gunicorn process if running on port 5000
//                 sh '''
//                     pkill -f "gunicorn" || true
//                 '''
//                 // Start the app with gunicorn in the background, binding to port 5000
//                 sh '''
//                     . ${VENV_DIR}/bin/activate
//                     nohup gunicorn --bind 0.0.0.0:5000 app:app > app.log 2>&1 &
//                 '''
//             }
//         }
//     }

//     post {
//         failure {
//             echo 'Deployment failed.'
//         }
//         success {
//             echo 'Deployed successfully.'
//         }
//     }
// }
