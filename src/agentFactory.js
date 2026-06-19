class AgentFactory {
    static compileAgent(agentType, taskDescription) {
        return `export default {
            async fetch(request, env, ctx) {
                if (request.method !== "POST") return new Response("Invalid Method", { status: 400 });
                try {
                    const payload = await request.json().catch(() => ({}));
                    const promptUser = payload.code || "";
                    const hfResponse = await fetch("https://api-inference.huggingface.co/models/Qwen/Qwen2.5-Coder-32B-Instruct", {
                        method: "POST",
                        headers: { "Authorization": "Bearer " + env.HUGGINGFACE_TOKEN, "Content-Type": "application/json" },
                        body: JSON.stringify({
                            inputs: "<|im_start|>system\\nSei un ingegnere software supremo. Rispondi in italiano.<|im_end|>\\n<|im_start|>user\\n" + promptUser + "<|im_end|>\\n<|im_start|>assistant\\n",
                            parameters: { max_new_tokens: 1024, temperature: 0.2 }
                        })
                    });
                    const hfData = await hfResponse.json();
                    let outputText = "Errore di elaborazione del modello Cloud.";
                    if (hfData && hfData.generated_text) { outputText = hfData.generated_text.split("<|im_start|>assistant\\n").pop(); }
                    else if (hfData[0] && hfData[0].generated_text) { outputText = hfData[0].generated_text; }
                    return new Response(JSON.stringify({ agent: "${agentType}", status: "Success", output: outputText }), { headers: { "content-type": "application/json" } });
                } catch (e) {
                    return new Response(JSON.stringify({ status: "error", output: e.message }), { headers: { "content-type": "application/json" } });
                }
            }
        };`;
    }
}
module.exports = AgentFactory;
