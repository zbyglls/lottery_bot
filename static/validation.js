// validation.js
function validateForm(event) {
    // 抽奖标题验证
    const title = document.getElementById('title').value;
    if (!title) {
        alert('请输入抽奖标题！');
        if (event) {
            event.preventDefault();
            event.stopPropagation(); // 阻止事件冒泡
        }
        return false;
    }


    // 图片或视频链接输入框验证
    const mediaType = document.getElementById('media-type').value;
    let link = '';
    if (mediaType === 'image') {
        link = document.getElementById('image-link').value;
    } else if (mediaType === 'video') {
        link = document.getElementById('video-link').value;
    }
    if ((mediaType === 'image' || mediaType === 'video') && !link) {
        alert('请输入图片或视频链接！');
        if (event) {
            event.preventDefault();
            event.stopPropagation(); // 阻止事件冒泡
        }
        return false;
    }

    // 抽奖文字说明验证
    const descriptionEditor = new Quill('#description-editor');
    const description = descriptionEditor.root.innerHTML;
    if (!description || description === '<p><br></p>') {
        alert('请输入抽奖文字说明！');
        if (event) {
            event.preventDefault();
            event.stopPropagation(); // 阻止事件冒泡
        }
        return false;
    }

    // 请选关键词群组选择框验证
    const joinMethod = document.querySelector('input[name="join_method"]:checked').value;
    if (joinMethod === 'send_keywords_in_group') {
        const keywordGroup = document.getElementById('keyword-group').value;
        if (!keywordGroup) {
            alert('请选择关键词群组！');
            if (event) {
                event.preventDefault();
                event.stopPropagation(); // 阻止事件冒泡
            }
            return false;
        }
        // 抽奖关键词输入框验证
        const lotteryKeyword = document.getElementById('lottery-keyword').value;
        if (!lotteryKeyword) {
            alert('请输入抽奖关键词！');
            if (event) {
                event.preventDefault();
                event.stopPropagation(); // 阻止事件冒泡
            }
            return false;
        }
    }

    // 需要成员加入的群或频道列表验证
    const groupTableBody = document.getElementById('group-table-body');
    const groupRows = groupTableBody.getElementsByTagName('tr');
    if (groupRows.length === 0) {
        alert('请添加需要成员加入的群或频道！');
        if (event) {
            event.preventDefault();
            event.stopPropagation(); // 阻止事件冒泡
        }
        return false;
    }

    // 根据开奖方式进行验证
    const drawMethod = document.querySelector('input[name="draw_method"]:checked').value;
    if (drawMethod === 'draw_when_full') {
        // 满人开奖时验证参与人数
        const participantCount = document.getElementById('participant-count').value;
        if (!participantCount || isNaN(participantCount) || parseInt(participantCount) <= 0) {
            alert('参与人数必须大于 0！');
            if (event) {
                event.preventDefault();
                event.stopPropagation();
            }
            return false;
        }
    } else if (drawMethod === 'draw_at_time') {
        // 定时开奖时验证开奖日期
        const drawDate = document.getElementById('draw-date').value;
        if (!drawDate) {
            alert('请选择开奖日期！');
            if (event) {
                event.preventDefault();
                event.stopPropagation();
            }
            return false;
        }
        const now = new Date();
        const selectedDate = new Date(drawDate);
        if (selectedDate <= now) {
            alert('开奖日期不能选择过去的时间！');
            if (event) {
                event.preventDefault();
                event.stopPropagation();
            }
            return false;
        }
    }

    // 奖品列表验证
    const prizeTableBody = document.getElementById('prize-table-body');
    const prizeRows = prizeTableBody.getElementsByTagName('tr');
    if (prizeRows.length === 0) {
        alert('请设置奖品！');
        if (event) {
            event.preventDefault();
            event.stopPropagation(); // 阻止事件冒泡
        }
        return false;
    }

    // 验证通知设置
    if (!validateNotifications()) {
        if (event) {
            event.preventDefault();
            event.stopPropagation();
        }
        return false;
    }

    return true;
}

// 添加判断奖品是否重复的函数
function isPrizeDuplicate(prizeName) {
    const prizeTableBody = document.getElementById('prize-table-body');
    const prizeRows = prizeTableBody.getElementsByTagName('tr');
    
    for (let i = 0; i < prizeRows.length; i++) {
        const existingPrizeName = prizeRows[i].getElementsByTagName('td')[0].textContent.trim();
        if (existingPrizeName === prizeName) {
            return true;
        }
    }
    return false;
}

// 修改 validateAddPrize 函数
function validateAddPrize() {
    // 奖品名称输入框验证
    const prizeName = document.getElementById('prize-name').value.trim();
    if (!prizeName) {
        alert('请输入奖品名称！');
        return false;
    }

    // 检查奖品名称是否重复
    if (isPrizeDuplicate(prizeName)) {
        alert('该奖品已存在，请勿重复添加！');
        return false;
    }

    // 奖品数量输入框验证
    const prizeCount = document.getElementById('prize-count').value;
    if (!prizeCount || isNaN(prizeCount) || parseInt(prizeCount) <= 0) {
        alert('奖品数量必须大于 0！');
        return false;
    }

    return true;
}

// 修改 validatePrize 函数，用于编辑奖品时的验证
function validatePrize(name, count, originalName) {
    // 验证奖品名称
    if (!name || name.trim() === '') {
        alert('请输入奖品名称！');
        return false;
    }

    // 如果奖品名称被修改了，则检查是否与其他奖品重复
    if (name.trim() !== originalName && isPrizeDuplicate(name.trim())) {
        alert('该奖品已存在，请更换奖品名称！');
        return false;
    }

    // 验证奖品数量
    if (!count || isNaN(count) || parseInt(count) <= 0) {
        alert('奖品数量必须大于0！');
        return false;
    }

    return true;
}

// 添加验证通知内容的函数
function validateNotifications() {
    // 获取通知内容
    const winnerPrivateNotice = document.getElementById('winner-private-notice-editor').querySelector('.ql-editor').innerHTML;
    const creatorPrivateNotice = document.getElementById('creator-private-notice-editor').querySelector('.ql-editor').innerHTML;
    const groupChannelNotice = document.getElementById('group-channel-notice-editor').querySelector('.ql-editor').innerHTML;

    // 中奖私聊中奖人通知验证
    if (!winnerPrivateNotice || winnerPrivateNotice === '<p><br></p>') {
        alert('请输入中奖私聊中奖人通知内容！');
        return false;
    }

    // 中奖私聊创建人通知验证
    if (!creatorPrivateNotice || creatorPrivateNotice === '<p><br></p>') {
        alert('请输入中奖私聊创建人通知内容！');
        return false;
    }

    // 中奖发送到群/频道通知验证
    if (!groupChannelNotice || groupChannelNotice === '<p><br></p>') {
        alert('请输入中奖发送到群/频道通知内容！');
        return false;
    }

    return true;
}