import * as vscode from 'vscode';
import axios from 'axios';

/**
 * Activates the extension. Called when the extension is first activated.
 * * @param context - The extension context provided by VSCode.
 */
export function activate(context: vscode.ExtensionContext) {
    console.log('Autonomous Engineer extension is now active!');

    // Register the command defined in package.json
    let disposable = vscode.commands.registerCommand('autonomous-engineer.submitTask', async () => {
        // 1. Prompt the user for the engineering goal
        const goal = await vscode.window.showInputBox({
            prompt: 'Enter your engineering task/goal for the Autonomous Agent',
            placeHolder: 'e.g., Refactor the authentication module to use PyJWT'
        });

        if (!goal) {
            return; // User canceled the input
        }

        vscode.window.showInformationMessage(`Sending task to Autonomous Engineer...`);

        try {
            // 2. Retrieve configuration settings (URL and API Key)
            const config = vscode.workspace.getConfiguration('autonomousEngineer');
            const apiUrl = config.get<string>('apiUrl', 'http://localhost:8000/api/v1/tasks/');
            const apiKey = config.get<string>('apiKey', 'default-dev-key');

            // 3. Determine the current workspace directory to send to the agent
            const workspaceFolders = vscode.workspace.workspaceFolders;
            const workspaceDir = workspaceFolders ? workspaceFolders[0].uri.fsPath : './workspace';

            // 4. Send the POST request to our FastAPI backend
            const response = await axios.post(apiUrl, {
                goal: goal,
                workspace_dir: workspaceDir
            }, {
                headers: {
                    'X-API-Key': apiKey,
                    'Content-Type': 'application/json'
                }
            });

            // 5. Notify the user of success
            const taskId = response.data.task_id;
            vscode.window.showInformationMessage(`Task Queued Successfully! Task ID: ${taskId}`);
            
        } catch (error: any) {
            console.error('API Error:', error);
            const errorMessage = error.response?.data?.detail || error.message;
            vscode.window.showErrorMessage(`Autonomous Engineer Error: ${errorMessage}`);
        }
    });

    context.subscriptions.push(disposable);
}

/**
 * Deactivates the extension. Called when VSCode shuts down.
 */
export function deactivate() {}