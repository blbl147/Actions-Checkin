const axios = require('axios');
const PUSHPLUS = process.env.PUSHPLUS;
const KANXUE_COOKIE = process.env.KANXUE_COOKIE;

// 添加日志输出工具类
class Logger {
    static info(msg) {
        console.log(`ℹ️ ${new Date().toLocaleString('zh-CN')} [INFO] ${msg}`);
    }

    static success(msg) {
        console.log(`✅ ${new Date().toLocaleString('zh-CN')} [SUCCESS] ${msg}`);
    }

    static warning(msg) {
        console.log(`⚠️ ${new Date().toLocaleString('zh-CN')} [WARNING] ${msg}`);
    }

    static error(msg) {
        console.log(`❌ ${new Date().toLocaleString('zh-CN')} [ERROR] ${msg}`);
    }
}

const checkCOOKIE = async () => {
    Logger.info("检查Cookie配置...");

    if (!KANXUE_COOKIE || !KANXUE_COOKIE.length) {
        Logger.error('不存在 KANXUE_COOKIE，请重新检查');
        return false;
    }

    const pairs = KANXUE_COOKIE.split(/\s*;\s*/);
    for (const pairStr of pairs) {
        if (!pairStr.includes('=')) {
            Logger.error(`存在不正确的 COOKIE，请重新检查`);
            return false;
        }
    }

    Logger.success("Cookie检查通过");
    return true;
}

const checkIn = async () => {
    Logger.info("=" * 60);
    Logger.info("🚀 看雪论坛自动签到开始");
    Logger.info("=" * 60);

    const options = {
        method: 'post',
        url: `https://bbs.kanxue.com/user-signin.htm`,
        headers: {
            'User-Agent': 'HD1910(Android/7.1.2) (pediy.UNICFBC0DD/1.0.5) Weex/0.26.0 720x1280',
            'Cookie': KANXUE_COOKIE,
            'Connection': 'keep-alive',
            'Accept': '*/*'
        }
    };

    Logger.info(`📡 目标地址: ${options.url}`);
    Logger.info(`📦 Cookie长度: ${KANXUE_COOKIE.length} 字符`);

    return axios(options).catch(error => {
        if (error.response) {
            Logger.error(`请求失败，状态码: ${error.response.status}`);
            Logger.info(`响应数据: ${JSON.stringify(error.response.data)}`);
        } else if (error.request) {
            Logger.error("网络请求失败，请检查网络连接");
            Logger.info(`请求详情: ${error.request}`);
        } else {
            Logger.error('发送请求时出错');
            Logger.info(`错误信息: ${error.message}`);
        }
        Logger.info(`错误配置: ${JSON.stringify(error.config)}`);
    });
};

const sendMsg = async (msg, code) => {
    const token = PUSHPLUS;
    if (!token) {
        Logger.warning("未配置 PUSHPLUS，跳过通知推送");
        return;
    }

    let title = '看雪论坛签到';
    let content;

    if (code == 0){
        content = `🎉🎉🎉签到成功，获得${msg}雪币`;
    } else {
        content = `📢您已签到，无需重复签到`;
    }

    Logger.info("准备推送签到结果通知...");

    const data = {
        token,
        title: title,
        content: content,
        template: 'json'
    };

    Logger.info(`推送数据: ${JSON.stringify({
        ...data,
        token: data.token.replace(/^(.{1,4})(.*)(.{4,})$/, (_, a, b, c) => a + b.replace(/./g, '*') + c)
    })}`);

    return axios({
        method: 'post',
        url: `http://www.pushplus.plus/send`,
        data
    }).then(response => {
        if (response.data && response.data.code === 200) {
            Logger.success("通知推送成功");
        } else {
            Logger.warning(`推送服务返回异常: ${JSON.stringify(response.data)}`);
        }
        return response;
    }).catch((error) => {
        if (error.response) {
            Logger.warning(`PUSHPLUS推送 请求失败，状态码：${error.response.status}`);
        } else if (error.request) {
            Logger.warning('PUSHPLUS推送 网络错误');
        } else {
            Logger.error(`通知推送异常: ${error.message}`);
        }
    });
};

const start = async () => {
    try {
        console.log(`
    ╔═══════════════════════════════════════╗
    ║     看雪论坛自动签到 - GitHub版       ║
    ╚═══════════════════════════════════════╝
        `);

        Logger.info("开始执行看雪论坛自动签到任务...");

        const checkCOOKIE_result = await checkCOOKIE();
        if (!checkCOOKIE_result) {
            Logger.error("Cookie检查失败，终止签到流程");
            return;
        }

        Logger.info("Cookie验证通过，开始签到请求...");
        const checkIn_result = await checkIn();

        if (!checkIn_result || !checkIn_result.data) {
            Logger.error("签到请求无响应，请检查网络或Cookie是否失效");
            return;
        }

        const message = checkIn_result.data.message;
        const code = checkIn_result.data.code;

        Logger.info(`签到响应: 状态码=${code}, 消息=${message}`);

        if (code == 0 || message == '您今日已签到成功') {
            if (code == 0) {
                Logger.success('签到成功');
                const rewardMatch = message.match(/获得(\d+)雪币/);
                if (rewardMatch) {
                    Logger.info(`🎉 签到成功，获得 ${rewardMatch[1]} 雪币`);
                }
            } else {
                Logger.info(message);
            }

            if (!PUSHPLUS || !PUSHPLUS.length) {
                Logger.warning('未配置 PUSHPLUS，跳过结果通知');
            } else {
                await sendMsg(message, code);
            }

            Logger.success("签到任务执行完成");
        } else {
            Logger.error(`签到失败: ${message}`);
        }
    } catch (error) {
        Logger.error(`签到过程中发生异常: ${error.message}`);
        Logger.info(error.stack);
    } finally {
        Logger.info("=" * 60);
    }
}

start();
