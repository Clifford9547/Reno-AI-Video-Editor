document.addEventListener('DOMContentLoaded', () => {
    const uploadForm = document.getElementById('upload-form');
    const videoFile = document.getElementById('videoFile');
    const uploadBtn = document.getElementById('upload-btn');
    const uploadProgressBarContainer = document.getElementById('upload-progress-container');
    const uploadProgressBar = document.getElementById('upload-progress-bar');
    const globalStatusText = document.getElementById('global-status-text');
    const llmProviderSelect = document.getElementById('llmProvider');

    const customApiUrlGroup = document.getElementById('customApiUrlGroup');
    const apiUrlInput = document.getElementById('apiUrl');

    // 选择不同提供者时，自动设置默认 API 地址
    llmProviderSelect.addEventListener('change', () => {
    const selected = llmProviderSelect.value;
    if (selected === 'custom') {
        customApiUrlGroup.style.display = 'block';
        apiUrlInput.value = ''; // 允许手动输入
    } else {
        customApiUrlGroup.style.display = 'none';
        if (selected === 'openai') {
        apiUrlInput.value = 'https://api.openai.com/v1/chat/completions';
        } else if (selected === 'gemini') {
        apiUrlInput.value = 'https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent';
        } else if (selected === 'claude') {
        apiUrlInput.value = 'https://api.anthropic.com/v1/messages';
        }
    }
    });


    const uploadSection = document.getElementById('upload-section');
    const scriptSection = document.getElementById('script-section');
    const originalScriptText = document.getElementById('original-script-text');
    const confirmScriptBtn = document.getElementById('confirm-script-btn');

    const aiSettingsSection = document.getElementById('ai-settings-section');
    const themeSelect = document.getElementById('theme');
    const targetAudienceInput = document.getElementById('targetAudience');
    const videoPurposeInput = document.getElementById('videoPurpose');
    const generateAiScriptBtn = document.getElementById('generate-ai-script-btn');
    const aiScriptProgressBarContainer = document.getElementById('ai-script-progress-container');
    const aiScriptProgressBar = document.getElementById('ai-script-progress-bar');

    const aiScriptPreviewSection = document.getElementById('ai-script-preview-section');
    const aiGeneratedScriptText = document.getElementById('ai-generated-script-text');
    const applyEffectsBtn = document.getElementById('apply-effects-btn');
    const videoGenProgressBarContainer = document.getElementById('video-gen-progress-container');
    const videoGenProgressBar = document.getElementById('video-gen-progress-bar');

    const finalVideoSection = document.getElementById('final-video-section');
    const downloadVideoLink = document.getElementById('download-video-link');
    const startOverBtn = document.getElementById('start-over-btn');

    let currentVideoId = null; // 用于存储当前处理视频的ID
    let pollingInterval = null; // 用于存储轮询的interval ID

    // --- 辅助函数 ---
    function setSectionState(sectionElement, isActive) {
        if (isActive) {
            sectionElement.classList.remove('disabled-section');
            sectionElement.classList.add('active-section');
        } else {
            sectionElement.classList.remove('active-section');
            sectionElement.classList.add('disabled-section');
        }
    }

    function updateProgressBar(progressBarElem, progress) {
        progressBarElem.style.width = progress + '%';
        // progressBarElem.textContent = progress + '%'; // 可以显示百分比文本
    }

    function setGlobalStatus(message) {
        globalStatusText.textContent = message;
    }

    // --- 状态管理函数 ---
    function resetUI() {
        setSectionState(uploadSection, true);
        setSectionState(scriptSection, false);
        setSectionState(aiSettingsSection, false);
        setSectionState(aiScriptPreviewSection, false);
        setSectionState(finalVideoSection, false);

        uploadForm.reset();
        originalScriptText.value = '';
        aiGeneratedScriptText.value = '';
        themeSelect.value = 'joyful'; // 恢复默认主题
        targetAudienceInput.value = '';
        videoPurposeInput.value = '';

        uploadProgressBarContainer.style.display = 'none';
        aiScriptProgressBarContainer.style.display = 'none';
        videoGenProgressBarContainer.style.display = 'none';
        updateProgressBar(uploadProgressBar, 0);
        updateProgressBar(aiScriptProgressBar, 0);
        updateProgressBar(videoGenProgressBar, 0);

        setGlobalStatus('');
        currentVideoId = null;
        if (pollingInterval) {
            clearInterval(pollingInterval);
            pollingInterval = null;
        }
    }

    // --- 阶段性处理函数 ---

    // 阶段 1: 视频上传与转录
    uploadForm.addEventListener('submit', async (event) => {
        event.preventDefault(); // 阻止表单默认提交行为

        setGlobalStatus('正在上传视频并进行转录...');
        setSectionState(uploadSection, false); // 禁用上传区
        uploadBtn.disabled = true;
        uploadProgressBarContainer.style.display = 'block';
        updateProgressBar(uploadProgressBar, 0);

        const formData = new FormData(uploadForm);

        try {
            const response = await fetch('/upload_and_transcribe', {
                method: 'POST',
                body: formData
            });

            const data = await response.json();
            if (response.ok) {
                currentVideoId = data.video_id;
                setGlobalStatus('视频上传成功，开始后台转录...');
                // 启动轮询来获取转录状态
                startPollingStatus('transcribe');
            } else {
                setGlobalStatus(`错误: ${data.message || '上传失败'}`);
                console.error('Upload Error:', data);
                resetUI(); // 失败则重置
            }
        } catch (error) {
            setGlobalStatus(`网络或服务器错误: ${error.message}`);
            console.error('Fetch Error:', error);
            resetUI();
        } finally {
            uploadBtn.disabled = false;
        }
    });

    // 阶段 2: 原始脚本确认
    confirmScriptBtn.addEventListener('click', () => {
        setSectionState(scriptSection, false);
        setSectionState(aiSettingsSection, true); // 激活 AI 设置区
        setGlobalStatus('请设置 AI 创作参数。');
    });

    // 阶段 3: AI 脚本生成
    generateAiScriptBtn.addEventListener('click', async () => {
        if (!currentVideoId) {
            setGlobalStatus('请先上传视频。');
            return;
        }
        setGlobalStatus('正在生成 AI 智能脚本...');
        setSectionState(aiSettingsSection, false); // 禁用 AI 设置区
        generateAiScriptBtn.disabled = true;
        aiScriptProgressBarContainer.style.display = 'block';
        updateProgressBar(aiScriptProgressBar, 0);

        const theme = themeSelect.value;
        const targetAudience = targetAudienceInput.value;
        const videoPurpose = videoPurposeInput.value;
        const originalScript = originalScriptText.value; // AI也需要原始脚本作为参考

        try {
            const response = await fetch('/generate_ai_script', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
              body: JSON.stringify({
                video_id: currentVideoId,
                original_script: originalScript,
                theme: theme,
                target_audience: targetAudience,
                video_purpose: videoPurpose,
                api_url: document.getElementById("apiUrl").value,
                api_method: document.getElementById("apiMethod").value,
                api_key: document.getElementById("apiKey").value,
                llm_provider: document.getElementById("llmProvider").value

                
            })

            });

            const data = await response.json();
            if (response.ok) {
                setGlobalStatus('AI 脚本生成中...');
                startPollingStatus('ai_script_gen');
            } else {
                setGlobalStatus(`错误: ${data.message || 'AI 脚本生成失败'}`);
                console.error('AI Script Gen Error:', data);
                resetUI();
            }
        } catch (error) {
            setGlobalStatus(`网络或服务器错误: ${error.message}`);
            console.error('Fetch Error:', error);
            resetUI();
        } finally {
            generateAiScriptBtn.disabled = false;
        }
    });

    // 阶段 4: 应用特效并生成视频
    applyEffectsBtn.addEventListener('click', async () => {
        if (!currentVideoId) {
            setGlobalStatus('请先上传视频并生成 AI 脚本。');
            return;
        }
        setGlobalStatus('正在应用特效并生成最终视频...');
        setSectionState(aiScriptPreviewSection, false); // 禁用预览区
        applyEffectsBtn.disabled = true;
        videoGenProgressBarContainer.style.display = 'block';
        updateProgressBar(videoGenProgressBar, 0);

        // 这里需要发送 AI 生成的脚本内容，或者让后端通过 video_id 找到
        const aiScript = aiGeneratedScriptText.value; 

        try {
            const response = await fetch('/generate_final_video', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    video_id: currentVideoId,
                    ai_script: aiScript // 发送AI生成的脚本
                    // 可以添加其他特效参数，如果前端有更多自定义选项
                })
            });

            const data = await response.json();
            if (response.ok) {
                setGlobalStatus('最终视频生成中...');
                startPollingStatus('video_gen');
            } else {
                setGlobalStatus(`错误: ${data.message || '最终视频生成失败'}`);
                console.error('Video Gen Error:', data);
                resetUI();
            }
        } catch (error) {
            setGlobalStatus(`网络或服务器错误: ${error.message}`);
            console.error('Fetch Error:', error);
        } finally {
            applyEffectsBtn.disabled = false;
        }
    });

    // --- 轮询状态函数 ---
    function startPollingStatus(stage) {
        if (pollingInterval) {
            clearInterval(pollingInterval); // 清除之前的轮询
        }

        pollingInterval = setInterval(async () => {
            if (!currentVideoId) {
                clearInterval(pollingInterval);
                return;
            }

            try {
                const response = await fetch(`/status_api/${currentVideoId}`);
                const statusData = await response.json();
                
                // 更新全局状态文本和对应阶段的进度条
                setGlobalStatus(statusData.message);
                if (stage === 'transcribe') {
                    updateProgressBar(uploadProgressBar, statusData.progress);
                } else if (stage === 'ai_script_gen') {
                    updateProgressBar(aiScriptProgressBar, statusData.progress);
                } else if (stage === 'video_gen') {
                    updateProgressBar(videoGenProgressBar, statusData.progress);
                }

                if (statusData.status === 'completed') {
                    clearInterval(pollingInterval);
                    if (stage === 'transcribe') {
                        // 转录完成，显示原始脚本区
                        originalScriptText.value = statusData.script_content || '未获取到脚本内容。'; // 从后端获取脚本内容
                        setSectionState(scriptSection, true);
                        setGlobalStatus('转录完成，请确认原始脚本。');
                    } else if (stage === 'ai_script_gen') {
                        // AI 脚本生成完成，显示 AI 脚本预览区
                        aiGeneratedScriptText.value = statusData.ai_script_content || 'AI 脚本生成失败。'; // 从后端获取 AI 脚本内容
                        setSectionState(aiScriptPreviewSection, true);
                        setGlobalStatus('AI 智能脚本已生成，请预览。');
                    } else if (stage === 'video_gen') {
                        // 最终视频生成完成，显示最终视频下载区
                        downloadVideoLink.href = `/download_video/${currentVideoId}`; // 假设有这个下载路由
                        setSectionState(finalVideoSection, true);
                        setGlobalStatus('最终视频已生成！');
                    }
                } else if (statusData.status === 'failed') {
                    clearInterval(pollingInterval);
                    setGlobalStatus(`处理失败: ${statusData.error || '未知错误'}`);
                    console.error('Processing failed:', statusData);
                    resetUI(); // 失败则重置所有
                }
            } catch (error) {
                console.error('Polling Error:', error);
                clearInterval(pollingInterval);
                setGlobalStatus('获取状态失败，请刷新页面。');
                resetUI();
            }
        }, 2000); // 每2秒轮询一次
    }

    // --- 重新开始按钮 ---
    startOverBtn.addEventListener('click', resetUI);

    // 初始化 UI 状态
    resetUI();
});