// script.js

// 全局变量
let groups = [];
let prizes = [];
let searchInput; 
let dropdown;
let messageSearchInput
let messageDropdown
let messageGroupId

// 将模态框相关函数移到全局作用域
function openModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        modal.classList.add('show');
        setTimeout(() => {
            modal.classList.add('fade-in');
        }, 50);
        modal.style.display = 'block';
    }
}

function closeModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        modal.classList.remove('fade-in');
        setTimeout(() => {
            modal.classList.remove('show');
            modal.style.display = 'none';
        }, 300);

        // 清空对应的输入框
        const inputId = modalId === 'add-group-modal' ? 'group-info' : 
                       modalId === 'add-prize-modal' ? 'prize-name' : null;
        if (inputId) {
            const input = document.getElementById(inputId);
            if (input) {
                input.value = '';
            }
        }
    }
}

async function getGroupInfo(input) {
    try {
        const response = await fetch(`/get_chat_info?query=${encodeURIComponent(input)}`);
        const data = await response.json();
        
        if (data.status === 'success') {
            // 检查是否已存在相同ID的群组
            const isDuplicate = groups.some(group => group.id === data.data.id);
            if (isDuplicate) {
                alert('该群组已添加，请勿重复添加');
                return;
            }
            
            // 添加到已有群组列表
            groups.push(data.data);
            
            // 更新表格显示
            renderGroups();
            
            // 关闭模态框
            closeModal('add-group-modal');
        } else {
            alert(data.message || '获取群组信息失败');
        }
    } catch (error) {
        console.error('获取群组信息失败:', error);
        alert('获取群组信息失败');
    }
}

function renderGroups() {
    const tableBody = document.getElementById('group-table-body');
    if (!tableBody) {
        console.error('找不到群组表格体');
        return;
    }
    
    // 清空现有内容
    tableBody.innerHTML = '';
    
    // 渲染群组列表
    if (groups && groups.length > 0) {
        groups.forEach(group => {
            const row = document.createElement('tr');
            row.innerHTML = `
                <td class="px-4 py-2">${group.id}</td>
                <td class="px-4 py-2">${group.username || '无'}</td>
                <td class="px-4 py-2">${group.title}</td>
                <td class="px-4 py-2">
                    <button onclick="removeGroup('${group.id}')" 
                            class="bg-red-500 text-white px-2 py-1 rounded" 
                            type="button">删除</button>
                </td>
            `;
            tableBody.appendChild(row);
        });
    }
}

function removeGroup(groupId) {
    if (confirm('确定要删除该群组吗？')) {
        groups = groups.filter(group => group.id !== groupId);
        renderGroups();
    }
}

// 防抖函数
function debounce(func, delay) {
    let timer = null;
    return function() {
        const context = this;
        const args = arguments;
        clearTimeout(timer);
        timer = setTimeout(() => {
            func.apply(context, args);
        }, delay);
    };
}
// 显示下拉列表
function showDropdown() {
    dropdown.classList.remove('hidden');
}

// 隐藏下拉列表
function hideDropdown() {
    dropdown.classList.add('hidden');
}
// 搜索处理
async function searchGroups() {
    if (!searchInput || !dropdown) {
        console.error('searchInput 或 dropdown 未正确初始化');
        return;
    }
    const query = searchInput.value;
    dropdown.innerHTML = '';

    if (query === '') {
        // 输入框未输入内容时显示空选项
        const li = document.createElement('li');
        li.textContent = '无有效选项';
        li.classList.add('p-2', 'text-gray-500', 'cursor-default');
        dropdown.appendChild(li);
        showDropdown();
        return;
    }

    try {
        const response = await fetch(`/get_chat_info?query=${encodeURIComponent(query)}`);
        if (!response.ok) {
            throw new Error('网络响应失败');
        }
        const data = await response.json();

        if (data.status === 'success') {
            const group = data.data;
            if (group.title) {
                const li = document.createElement('li');
                li.textContent = group.title; 
                li.classList.add('p-2', 'hover:bg-gray-100');
                li.addEventListener('click', () => {
                    searchInput.value = group.title;
                    // 添加隐藏字段存储群组ID
                    let hiddenInput = document.getElementById('keyword_group_id');
                    if (!hiddenInput) {
                        hiddenInput = document.createElement('input');
                        hiddenInput.type = 'hidden';
                        hiddenInput.id = 'keyword_group_id';
                        hiddenInput.name = 'keyword_group_id';
                        searchInput.parentNode.appendChild(hiddenInput);
                    }
                    hiddenInput.value = group.id;
                    hideDropdown();
                });
                dropdown.appendChild(li);
            } else {
                // 查询不到结果时显示空选项
                const li = document.createElement('li');
                li.textContent = '未找到相关群组';
                li.classList.add('p-2', 'text-gray-500', 'cursor-default');
                dropdown.appendChild(li);
            }
        } else {
            console.error('搜索失败:', data);
            const li = document.createElement('li');
            li.textContent = '未找到相关群组';
            li.classList.add('p-2', 'text-gray-500', 'cursor-default');
            dropdown.appendChild(li);
        }

        showDropdown();

    } catch (error) {
        console.error('搜索群组时出错:', error);
        const li = document.createElement('li');
        li.textContent = '搜索出错，请检查网络';
        li.classList.add('p-2', 'text-gray-500', 'cursor-default');
        dropdown.appendChild(li);
        showDropdown();
    }
}

// 显示发言群组下拉列表
function showMessageDropdown() {
    messageDropdown.classList.remove('hidden');

}

// 隐藏发言群组下拉列表
function hideMessageDropdown() {
    messageDropdown.classList.add('hidden');
}

// 搜索发言群组
async function searchMessageGroups() {
    if (!messageSearchInput || !messageDropdown) {
        console.error('messageSearchInput 或 messageDropdown 未正确初始化');
        return;
    }

    const query = messageSearchInput.value;
    messageDropdown.innerHTML = '';

    if (query === '') {
        const li = document.createElement('li');
        li.textContent = '无有效选项';
        li.classList.add('p-2', 'text-gray-500', 'cursor-default');
        messageDropdown.appendChild(li);
        showMessageDropdown();
        return;
    }

    try {
        const response = await fetch(`/get_chat_info?query=${encodeURIComponent(query)}`);
        if (!response.ok) {
            throw new Error('网络响应失败');
        }
        const data = await response.json();

        if (data.status === 'success') {
            const group = data.data;
            if (group.title) {
                const li = document.createElement('li');
                li.textContent = group.title;
                li.classList.add('p-2', 'hover:bg-gray-100', 'cursor-pointer');
                li.addEventListener('click', () => {
                    messageSearchInput.value = group.title;
                    // 添加隐藏字段存储群组ID
                    let hiddenInput = document.getElementById('message_group_id');
                    if (!hiddenInput) {
                        hiddenInput = document.createElement('input');
                        hiddenInput.type = 'hidden';
                        hiddenInput.id = 'message_group_id';
                        hiddenInput.name = 'message_group_id';
                        messageSearchInput.parentNode.appendChild(hiddenInput);
                    }
                    hiddenInput.value = group.id;
                    hideMessageDropdown();
                });
                messageDropdown.appendChild(li);
            } else {
                const li = document.createElement('li');
                li.textContent = '未找到相关群组';
                li.classList.add('p-2', 'text-gray-500', 'cursor-default');
                messageDropdown.appendChild(li);
            }
        } else {
            console.error('搜索失败:', data);
            const li = document.createElement('li');
            li.textContent = '未找到相关群组';
            li.classList.add('p-2', 'text-gray-500', 'cursor-default');
            messageDropdown.appendChild(li);
        }

        showMessageDropdown();

    } catch (error) {
        console.error('搜索群组时出错:', error);
        const li = document.createElement('li');
        li.textContent = '搜索出错，请检查网络';
        li.classList.add('p-2', 'text-gray-500', 'cursor-default');
        messageDropdown.appendChild(li);
        showMessageDropdown();
    }
}


document.addEventListener('DOMContentLoaded', () => {
    // 将函数添加到window对象
    window.openModal = openModal;
    window.closeModal = closeModal;
    window.getGroupInfo = getGroupInfo;
    window.renderGroups = renderGroups;
    window.removeGroup = removeGroup;
    window.searchGroups = searchGroups;
    window.debounce = debounce;
    window.showDropdown = showDropdown;
    window.hideDropdown = hideDropdown;
    window.showMessageDropdown = showMessageDropdown;
    window.hideMessageDropdown = hideMessageDropdown;
    window.searchMessageGroups = searchMessageGroups;


    // 此函数用于切换显示不同的选项卡
    function showTab(tabId) {
        const tabs = ['basic-info', 'prize-settings'];
        tabs.forEach(tab => {
            document.getElementById(tab).classList.add('hidden');
        });
        document.getElementById(tabId).classList.remove('hidden');
    }
    window.showTab = showTab;

    document.getElementById('add-group-btn').addEventListener('click', function () {
        openModal('add-group-modal');
    });
    
    // 绑定关闭添加群组模态框的事件
    document.getElementById('close-add-group-modal').addEventListener('click', function (event) {
        event.stopPropagation(); // 阻止事件冒泡
        closeModal('add-group-modal');
    });
    document.getElementById('cancel-add-group').addEventListener('click', function (event) {
        event.stopPropagation(); // 阻止事件冒泡
        closeModal('add-group-modal');
    });
    
    // 绑定关闭添加奖品模态框的事件
    document.getElementById('close-add-prize-modal').addEventListener('click', function () {
        closeModal('add-prize-modal');
    });
    document.getElementById('cancel-add-prize').addEventListener('click', function () {
        closeModal('add-prize-modal');
        document.getElementById('edit-prize-name').value = '';
        document.getElementById('edit-prize-count').value = '';
    });
    
    // 绑定关闭编辑奖品模态框的事件
    document.getElementById('close-edit-prize-modal').addEventListener('click', function () {
        closeModal('edit-prize-modal');
    });
    document.getElementById('cancel-edit-prize').addEventListener('click', function () {
        closeModal('edit-prize-modal');
        document.getElementById('edit-prize-name').value = '';
        document.getElementById('edit-prize-count').value = '';
    });

    renderGroups();
    
    // 确认添加群组按钮点击事件
    document.getElementById('confirm-add-group').addEventListener('click', function() {
        const input = document.getElementById('group-info').value.trim();
        if (!input) {
            alert('请输入群组/频道信息');
            return;
        }
        getGroupInfo(input);
    });

    document.getElementById('add-prize-btn').addEventListener('click', function () {
        openModal('add-prize-modal');
    });

    // 确认添加奖品
    document.getElementById('confirm-add-prize').addEventListener('click', function () {
        if (validateAddPrize()) {
            const name = document.getElementById('prize-name').value;
            const totalCount = document.getElementById('prize-count').value;
            // 将新奖品添加到数组中
            prizes.push({ name, totalCount });
            // 关闭模态框
            closeModal('add-prize-modal');
            // 清空输入框
            document.getElementById('prize-name').value = '';
            document.getElementById('prize-count').value = '';
            // 重新渲染奖品列表
            loadPrizes();
        }
    });

    // 此函数用于加载奖品列表，从前端数组中获取奖品信息，并将其显示在表格中
    function loadPrizes() {
        const tableBody = document.getElementById('prize-table-body');
        tableBody.innerHTML = '';
        prizes.forEach((prize, index) => {
            const row = document.createElement('tr');
            row.innerHTML = `
                <td class="px-4 py-2">${prize.name}</td>
                <td class="px-4 py-2">${prize.totalCount}</td>
                <td class="px-4 py-2">
                    <button onclick="editPrize(${index}, '${prize.name}', ${prize.totalCount})" class="bg-yellow-500 text-white px-2 py-1 rounded">编辑</button>
                    <button onclick="deletePrize(${index})" class="bg-red-500 text-white px-2 py-1 rounded">删除</button>
                </td>
            `;
            tableBody.appendChild(row);
        });
    }

    // 删除奖品，从前端数组中移除该奖品并重新渲染列表
    function deletePrize(index) {
        if (confirm('是否删除该奖品？')) {
            prizes.splice(index, 1);
            loadPrizes();
        }
    }
    window.deletePrize = deletePrize;

    // 编辑奖品，将奖品信息填充到编辑模态框中，并打开模态框
    function editPrize(index, name, totalCount) {
        document.getElementById('edit-prize-index').value = index;
        document.getElementById('edit-prize-name').value = name;
        document.getElementById('edit-prize-count').value = totalCount;
        openModal('edit-prize-modal');
    }
    window.editPrize = editPrize;

    // 确认编辑奖品”按钮，更新前端数组中的奖品信息并重新渲染列表
    document.getElementById('confirm-edit-prize').addEventListener('click', function () {
        const index = document.getElementById('edit-prize-index').value;
        const name = document.getElementById('edit-prize-name').value;
        const totalCount = document.getElementById('edit-prize-count').value;
        // 添加验证
        if (!validatePrize(name, totalCount)) {
            return;
        }
        prizes[index] = { name, totalCount };
        closeModal('edit-prize-modal');
        loadPrizes();
        alert('奖品编辑成功');
    });

    const mediaTypeSelect = document.getElementById('media-type');
    const imageLinkContainer = document.getElementById('image-link-container');
    const videoLinkContainer = document.getElementById('video-link-container');

    function updateLinkVisibility() {
        const selectedValue = mediaTypeSelect.value;
        if (selectedValue === 'image') {
            imageLinkContainer.classList.remove('hidden');
            videoLinkContainer.classList.add('hidden');
        } else if (selectedValue === 'video') {
            videoLinkContainer.classList.remove('hidden');
            imageLinkContainer.classList.add('hidden');
        } else {
            imageLinkContainer.classList.add('hidden');
            videoLinkContainer.classList.add('hidden');
        }
    }

    updateLinkVisibility();
    mediaTypeSelect.addEventListener('change', updateLinkVisibility);

    // 获取取消抽奖按钮
    const cancelLotteryBtn = document.getElementById('cancel-lottery-btn');

    cancelLotteryBtn.addEventListener('click', () => {
        // 弹出确认框，让用户确认是否取消抽奖
        if (confirm('你确定要取消本次抽奖吗？')) {
            // 模拟抽奖 ID，实际应用中应从页面或数据中获取
            const lotteryId = document.getElementById('lottery_id').value;

            // 发送请求到后端取消抽奖
            fetch(`/cancel_lottery?lottery_id=${lotteryId}`, {
                method: 'GET'
            })
            .then(response => response.json())
            .then(data => {
                if (data.status === 'success') {
                    window.location.reload();
                } else {
                    // 取消失败，给出提示
                    alert('取消抽奖失败，请稍后重试');
                }
            })
            .catch(error => {
                console.error('请求出错:', error);
                alert('网络错误，请稍后重试');
            });
        }
    });

    // 获取参与方式的单选按钮和相关的容器元素
    const joinMethodRadios = document.querySelectorAll('input[name="join_method"]');
    const groupKeywordFields = document.getElementById('group-keyword-fields');
    const groupMessageFields = document.getElementById('group-message-fields');

    // 监听参与方式的选择变化
    function handleJoinMethodChange() {
            // 先隐藏所有相关字段
        groupKeywordFields.classList.add('hidden');
        groupMessageFields.classList.add('hidden');
        // 获取当前选中的参与方式
        const selectedMethod = document.querySelector('input[name="join_method"]:checked').value;
        const hiddenInput = document.querySelector('input[name="keyword_group_id"]');
        if (hiddenInput && selectedMethod !== 'send_keywords_in_group') {
            hiddenInput.remove();
        }
        // 根据选择显示对应字段
        switch(selectedMethod) {
            case 'send_keywords_in_group':
                groupKeywordFields.classList.remove('hidden');
                break;
            case 'send_messages_in_group':
                groupMessageFields.classList.remove('hidden');
                break;
            // 默认情况（private_chat_bot）保持所有字段隐藏
            default:
                break;
        }
    }

    // 为所有参与方式单选按钮添加事件监听
    joinMethodRadios.forEach(radio => {
        radio.addEventListener('change', handleJoinMethodChange);
    });

    // 初始化时调用一次，确保初始状态正确
    handleJoinMethodChange();


    // 获取开奖方式的单选按钮和相关的容器元素
    const fullParticipantsRadio = document.getElementById('full-participants');
    const timedDrawRadio = document.getElementById('timed-draw');
    const participantCountContainer = document.getElementById('participant-count-container');
    const drawDateContainer = document.getElementById('draw-date-container');

    // 监听开奖方式的选择变化
    function handleDrawMethodChange() {
        if (fullParticipantsRadio.checked) {
            participantCountContainer.classList.remove('hidden');
            drawDateContainer.classList.add('hidden');
        } else if (timedDrawRadio.checked) {
            participantCountContainer.classList.add('hidden');
            drawDateContainer.classList.remove('hidden');
        }
    }

    // 初始化时调用一次，确保初始状态正确
    handleDrawMethodChange();

    // 为单选按钮添加事件监听器
    fullParticipantsRadio.addEventListener('change', handleDrawMethodChange);
    timedDrawRadio.addEventListener('change', handleDrawMethodChange);

    // 初始化抽奖文字说明编辑器
    const descriptionEditor = new Quill('#description-editor', {
        theme: 'snow'
    });
    // 监听编辑器内容变化，实时更新隐藏输入框的值
    descriptionEditor.on('text-change', () => {
        const descriptionElement = document.getElementById('description');
        if (descriptionElement) {
            const descriptionText = descriptionEditor.root.textContent;
            descriptionElement.value = descriptionText;
        }
    });

    // 获取元素
    searchInput = document.getElementById('keyword-group-search');
    messageSearchInput = document.getElementById('message-group-search');
    dropdown = document.getElementById('keyword-group-dropdown');
    messageDropdown = document.getElementById('message-group-dropdown');
    // 使用防抖函数包装 searchGroups，debouncedSearchMessageGroups
    const debouncedSearchGroups = debounce(searchGroups, 300);
    const debouncedSearchMessageGroups = debounce(searchMessageGroups, 300);

    // 监听输入事件
    searchInput.addEventListener('input', debouncedSearchGroups);
    messageSearchInput.addEventListener('input', debouncedSearchMessageGroups);

    // 点击页面其他地方隐藏下拉列表
    document.addEventListener('click', (event) => {
        if (!searchInput.contains(event.target) && !dropdown.contains(event.target)) {
            hideDropdown();
        }
        if (!messageSearchInput.contains(event.target) && !messageDropdown.contains(event.target)) {
            hideMessageDropdown();
        }
    });

    // 监听表单提交事件
    const submitButton = document.getElementById('submit-lottery-btn');
    document.getElementById('lottery-form').addEventListener('submit', async function (event) {
        event.stopPropagation();
        event.preventDefault(); // 首先阻止表单默认提交
        if (!validateForm()) {
            console.log('表单验证失败，终止提交');
            return false;
        }
    
        // 提交开始，禁用提交按钮
        submitButton.disabled = true;
        submitButton.style.opacity = '0.5'; // 视觉上提示按钮已禁用
        descriptionEditor.updateContents();


         // 封装同步内容的逻辑
        function syncEditorContents(form) {
            const formData = new FormData(form);
            // 处理媒体内容
            const mediaType = document.getElementById('media-type').value;
            if (mediaType && mediaType !== 'none') {
                formData.set('media_type', mediaType);
                const mediaUrl = mediaType === 'image' ? 
                    document.getElementById('image-link')?.value : 
                    document.getElementById('video-link')?.value;
                    
                if (mediaUrl) {
                    formData.set('media_url', mediaUrl);
                }
            }
            // 同步抽奖文字说明编辑器内容到隐藏输入框
            const descriptionElement = document.getElementById('description');
            if (descriptionEditor && descriptionElement) {
                const descriptionText = descriptionEditor.root.textContent;
                descriptionElement.value = descriptionText;
            } 
            // 获取参与方式
            const joinMethod = formData.get('join_method');
            // 处理关键词参与方式
            if (joinMethod === 'send_keywords_in_group') {
                const keywordGroupId = document.getElementById('keyword_group_id')?.value;
                const keyword = formData.get('keyword')?.trim();
                if (keywordGroupId) {
                    formData.set('keyword_group_id', keywordGroupId);
                }
                if (keyword) {
                    formData.set('keyword', keyword);
                }
            }
            // 处理群组发言参与方式
            else if (joinMethod === 'send_messages_in_group') {
                const messageGroupId = document.getElementById('message_group_id')?.value;
                if (messageGroupId) {
                    formData.set('message_group_id', messageGroupId);
                }
                const messageCount = formData.get('message_count');
                const messageCheckTime = formData.get('message_check_time');
                if (messageCount) {
                    formData.set('message_count', messageCount);
                }
                if (messageCheckTime) {
                    formData.set('message_check_time', messageCheckTime);
                }
            }
            // 获取需要成员加入的群或频道列表信息
            const groupTableBody = document.getElementById('group-table-body');
            const groupRows = groupTableBody.getElementsByTagName('tr');
            for (let i = 0; i < groupRows.length; i++) {
                const groupCells = groupRows[i].getElementsByTagName('td');
                const groupId = groupCells[0].textContent;
                formData.append('group_ids', groupId);
            }
            // 获取奖品信息
            const prizeTableBody = document.getElementById('prize-table-body');
            const rows = prizeTableBody.getElementsByTagName('tr');
            for (let i = 0; i < rows.length; i++) {
                const cells = rows[i].getElementsByTagName('td');
                const prizeName = cells[0].textContent;
                const prizeCount = cells[1].textContent;
                formData.append('prize_name', prizeName);
                formData.append('prize_count', prizeCount);
            }
            // 处理开奖时间
            const drawMethod = formData.get('draw_method');
            if (drawMethod === 'draw_at_time') {
                const localDrawTime = formData.get('draw_time');
                const utcDrawTime = convertToUTC(localDrawTime);
                formData.set('draw_time', utcDrawTime);  // 替换为UTC格式
                
            }else if (drawMethod === 'draw_when_full') {
                const participantCount = formData.get('participant_count');
                if (participantCount) {
                    formData.set('participant_count', participantCount);
                }
            }
            // 移除所有空值字段
            for (const [key, value] of Array.from(formData.entries())) {
                if (!value || value === 'none' || value === '') {
                    formData.delete(key);
                }
            }
            return formData;
        }
        const formData = syncEditorContents(this);

        setTimeout(async () => {
            try {
                // 提交表单数据
                const response = await fetch('/create_lottery', {
                    method: 'POST',
                    body: formData
                });
                const result = await response.json();
                if (result.status === 'success') {
                    alert('抽奖创建成功');
                } else {
                    alert('抽奖创建失败：' + result.message);
                    // 提交失败，重新启用提交按钮
                    submitButton.disabled = false;
                    submitButton.style.opacity = '1';
                }
            } catch (error) {
                console.error('创建抽奖出错:', error);
                alert('创建抽奖时发生错误');
                // 提交出错，重新启用提交按钮
                submitButton.disabled = false;
                submitButton.style.opacity = '1';
            }
        }, 200);
    });
});


// 检测移动设备
function isMobile() {
    return window.matchMedia("(max-width: 640px)").matches;
}

// 移动端优化
if(isMobile()) {
    // 增大点击区域
    document.querySelectorAll('button, a, input[type="radio"], input[type="checkbox"]').forEach(el => {
        el.style.minHeight = '44px';
        el.style.minWidth = '44px';
    });
    
    // 优化表单输入
    document.querySelectorAll('input, select, textarea').forEach(el => {
        el.style.fontSize = '16px'; // 防止iOS自动缩放
    });
}

// 添加时区转换函数
function convertToUTC(localTime) {
    // 将本地时间转换为ISO格式(YYYY-MM-DDTHH:mm:ssZ)
    const date = new Date(localTime);
    return date.toISOString();

}