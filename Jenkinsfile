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
        ZAP_PORT = '8090' // ZAP's listening port to avoid conflict with Jenkins agent
        
        // URLs as Groovy strings for robust handling
        ZAP_DOWNLOAD_URL = "https://github.com/zaproxy/zap-archive/releases/download/zap-v${ZAP_VERSION}/ZAP_${ZAP_VERSION}_Linux.tar.gz"
        PYPI_SIMPLE_URL = "https://pypi.org/simple/" // Kept for reference, no longer directly used for pip install
        ZAP_API_VERSION_URL = "http://localhost:${ZAP_PORT}/JSON/core/view/version/" // ZAP API endpoint for status check
        ZAP_SPIDER_API = "http://localhost:${ZAP_PORT}/JSON/spider/action/scan/" // ZAP Spider API endpoint (NEW)
        ZAP_ASCSAN_API = "http://localhost:${ZAP_PORT}/JSON/ascan/action/scan/" // ZAP Active Scan API endpoint
        ZAP_REPORT_API = "http://localhost:${ZAP_PORT}/JSON/core/action/htmlreport/" // ZAP Report API endpoint

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
                echo "Starting application locally with gunicorn from virtual environment..."
                sh "nohup ${env.VENV_DIR}/bin/gunicorn --bind 0.0.0.0:${env.APP_PORT} app:app > app.log 2>&1 &"
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
                echo "Starting Flask development server from virtual environment..."
                sh "nohup ${env.VENV_DIR}/bin/python3 app.py > flask_app.log 2>&1 &"
                echo "Waiting 10 seconds for Flask app to start..."
                sleep 10
                echo "Verifying Flask app is running at ${env.APP_URL}..."
                sh "curl --fail ${env.APP_URL}"
                echo "App is running for DAST scan!"
            }
        }

        stage('DAST Scan (OWASP ZAP)') {
            steps {
                echo "Starting DAST Scan on ${env.APP_URL}"

                // --- ZAP Installation (download and extract if not present) ---
                script {
                    sh "mkdir -p ${env.ZAP_BASE_DIR}"
                    if (!fileExists("${env.ZAP_HOME}/zap.sh")) {
                        echo "Downloading and extracting OWASP ZAP ${env.ZAP_VERSION}..."
                        sh "wget --no-verbose ${env.ZAP_DOWNLOAD_URL} -O ${env.ZAP_TAR_GZ}"
                        sh "tar -xzf ${env.ZAP_TAR_GZ} -C ${env.ZAP_BASE_DIR}"
                        sh "rm ${env.ZAP_TAR_GZ}"
                        // Ensure zap.sh is executable after extraction
                        sh "chmod +x ${env.ZAP_HOME}/zap.sh"
                    } else {
                        echo "OWASP ZAP ${env.ZAP_VERSION} already extracted."
                    }
                }

                // --- Start ZAP in Daemon Mode ---
                echo "Checking if port ${env.ZAP_PORT} is already in use before starting ZAP..."
                sh "lsof -i :${env.ZAP_PORT} || echo 'Port ${env.ZAP_PORT} is free or lsof not available/working.'"
                echo "Starting ZAP daemon on port ${env.ZAP_PORT}..."
                sh "nohup ${env.ZAP_HOME}/zap.sh -daemon -port ${env.ZAP_PORT} -host 0.0.0.0 -config api.disablekey=true > zap_daemon.log 2>&1 &"

                // --- Wait for ZAP daemon to start and be ready ---
                script {
                    def zapReady = false
                    timeout(time: 5, unit: 'MINUTES') { // Increased timeout to 5 minutes
                        while (!zapReady) {
                            try {
                                echo "Checking ZAP API endpoint (${env.ZAP_API_VERSION_URL})..."
                                sh "curl --fail --silent ${env.ZAP_API_VERSION_URL}"
                                zapReady = true
                                echo "ZAP daemon is ready."
                            } catch (e) {
                                echo "Waiting for ZAP daemon to start (checking every 10s)..."
                                sleep 10
                            }
                        }
                    }
                }

                // --- Trigger ZAP Spider (Crawl) via API (NEW STEP) ---
                echo "Triggering ZAP spider (crawl) on ${env.APP_URL} via API..."
                script {
                    // Trigger the spider, capture spider ID
                    def spiderResponse = sh(script: "curl -s \"${env.ZAP_SPIDER_API}?url=${env.APP_URL}&recurse=true\"", returnStdout: true).trim()
                    def jsonSlurper = new groovy.json.JsonSlurper()
                    def parsedResponse = jsonSlurper.parseText(spiderResponse)
                    def spiderId = parsedResponse.scan // ZAP spider API returns scan ID as 'scan'

                    if (!spiderId) {
                        error "Failed to start ZAP spider. Response: ${spiderResponse}"
                    }
                    echo "ZAP spider started with ID: ${spiderId}"

                    // Wait for spider to complete
                    def spiderComplete = false
                    timeout(time: 3, unit: 'MINUTES') { // Max 3 minutes for spider
                        while (!spiderComplete) {
                            def statusJson = sh(script: "curl -s http://localhost:${env.ZAP_PORT}/JSON/spider/view/status/?scanId=${spiderId}", returnStdout: true).trim()
                            
                            def status = -1
                            try {
                                def parsedJson = jsonSlurper.parseText(statusJson)
                                if (parsedJson && parsedJson.status) {
                                    status = parsedJson.status.toInteger()
                                }
                            } catch (e) {
                                echo "Could not parse ZAP spider status JSON: ${statusJson}. Error: ${e.message}"
                            }

                            if (status == 100) {
                                echo "ZAP spider 100% complete."
                                spiderComplete = true
                            } else {
                                echo "ZAP spider progress: ${status}%"
                                sleep 10
                            }
                        }
                    }
                }

                // --- Trigger ZAP Active Scan via API ---
                echo "Triggering ZAP active scan on ${env.APP_URL} via API..."
                script {
                    // Trigger active scan, capture scan ID
                    def ascanResponse = sh(script: "curl -s \"${env.ZAP_ASCSAN_API}?url=${env.APP_URL}&recurse=true\"", returnStdout: true).trim()
                    def jsonSlurper = new groovy.json.JsonSlurper()
                    def parsedResponse = jsonSlurper.parseText(ascanResponse)
                    def ascanId = parsedResponse.scan // ZAP ascan API returns scan ID as 'scan'

                    if (!ascanId) {
                        error "Failed to start ZAP active scan. Response: ${ascanResponse}"
                    }
                    echo "ZAP active scan started with ID: ${ascanId}"

                    // Wait for active scan to complete
                    def ascanComplete = false
                    timeout(time: 5, unit: 'MINUTES') { // Max 5 minutes for active scan
                        while (!ascanComplete) {
                            def statusJson = sh(script: "curl -s http://localhost:${env.ZAP_PORT}/JSON/ascan/view/status/?scanId=${ascanId}", returnStdout: true).trim()
                            
                            def status = -1
                            try {
                                def parsedJson = jsonSlurper.parseText(statusJson)
                                if (parsedJson && parsedJson.status) {
                                    status = parsedJson.status.toInteger()
                                }
                            } catch (e) {
                                echo "Could not parse ZAP active scan status JSON: ${statusJson}. Error: ${e.message}"
                            }

                            if (status == 100) {
                                echo "ZAP active scan 100% complete."
                                ascanComplete = true
                            } else {
                                echo "ZAP active scan progress: ${status}%"
                                sleep 15
                            }
                        }
                    }
                }

                // --- Generate HTML Report via API ---
                echo "Generating ZAP HTML report..."
                script {
                    sh "mkdir -p target/zap-reports" // Ensure directory exists
                    sh "curl -s -o target/zap-reports/zap-report.html \"${env.ZAP_REPORT_API}?formMethod=GET&form=htmlreport\""
                }
            }
            post {
                always {
                    script {
                        echo "Shutting down ZAP daemon..."
                        sh "pkill -f 'zap.sh' || true"
                        sleep 5

                        echo "Checking if port ${env.ZAP_PORT} is still in use after ZAP shutdown..."
                        sh "lsof -i :${env.ZAP_PORT} || echo 'Port ${env.ZAP_PORT} is free after ZAP shutdown or lsof not available/working.'"

                        echo "Killing Flask app processes on port ${env.APP_PORT}..."
                        def appPids = sh(script: "lsof -t -i :${env.APP_PORT}", returnStdout: true).trim().split('\\s+')
                        appPids = appPids.findAll { it.trim() != '' }

                        if (appPids) {
                            echo "Found PIDs: ${appPids.join(' ')}"
                            for (pid in appPids) {
                                try {
                                    sh "kill ${pid}"
                                } catch (e) {
                                    echo "Warning: Failed to kill process ${pid}: ${e.message}. It might have already exited."
                                }
                            }
                        } else {
                            echo "No Flask app process found on port ${env.APP_PORT} to kill."
                        }
                    }
                    archiveArtifacts artifacts: 'target/zap-reports/**/*.html', allowEmptyArchive: true
                    echo "ZAP DAST scan completed and application cleaned up."

                    // Archiving ZAP daemon log for inspection (even if pipeline failed)
                    echo "Archiving ZAP daemon log for inspection..."
                    archiveArtifacts artifacts: 'zap_daemon.log', onlyIfSuccessful: false, allowEmptyArchive: true
                }
                failure {
                    echo "ZAP DAST scan detected vulnerabilities or failed to complete successfully! Check zap_daemon.log for details."
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
