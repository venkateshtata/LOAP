## Usage Instructions


### 1. Establish an SSH Tunnel

To securely forward the Streamlit app to your local machine, run the following command:

```bash
ssh -L 8501:localhost:8501 root@{IP_ADDRESS}
```

- Replace `{IP_ADDRESS}` with the actual IP address of your remote server.
- This command forwards port `8501` from the remote server to your local machine.


### 2. Running `ollama start` in a `tmux` Session

**Start a new `tmux` session:**
   ```bash
   tmux new -s ollama_session
   ```
   ```bash
   ollama start
   ```
   Press to dettach:
   ```
   Ctrl + B, then D
   ```


### 3. Run the Streamlit Application

After successfully connecting via SSH, execute the following command on the remote server:

```bash
streamlit run chatbot_agent_venkat_2.py --server.port 8501 --server.address 0.0.0.0
```

- This starts the Streamlit app on port `8501`, accessible to all network interfaces.

### 4. Access the Streamlit App

On your local machine, open a web browser and navigate to:

```
http://localhost:8501
```

You should now see the chatbot application running.
