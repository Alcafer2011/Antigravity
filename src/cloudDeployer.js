const https = require("https");

class CloudDeployer {
    static deployToCloudflare(accountId, apiToken, scriptName, scriptContent) {
        return new Promise((resolve) => {
            const options = {
                hostname: "api.cloudflare.com",
                path: `/client/v4/accounts/${accountId}/workers/scripts/${scriptName}`,
                method: "PUT",
                headers: { 
                    "Authorization": `Bearer ${apiToken}`, 
                    "Content-Type": "application/javascript" 
                }
            };
            
            const req = https.request(options, (res) => {
                let chunks = [];
                res.on('data', chunk => chunks.push(chunk));
                res.on('end', () => {
                    const body = Buffer.concat(chunks).toString();
                    try {
                        const jsonResponse = JSON.parse(body);
                        if (res.statusCode >= 200 && res.statusCode < 300) {
                            resolve({ success: true, url: `https://${scriptName}.${accountId}.workers.dev`, data: jsonResponse });
                        } else {
                            resolve({ success: false, error: body, statusCode: res.statusCode });
                        }
                    } catch (e) {
                        if (res.statusCode >= 200 && res.statusCode < 300) {
                            resolve({ success: true, url: `https://${scriptName}.${accountId}.workers.dev` });
                        } else {
                            resolve({ success: false, error: body, statusCode: res.statusCode });
                        }
                    }
                });
            });
            
            req.on('error', (error) => {
                resolve({ success: false, error: error.message });
            });
            
            req.write(scriptContent);
            req.end();
        });
    }
}

module.exports = CloudDeployer;
