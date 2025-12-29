<template>
  <div class="help-page">
    <!-- 顶部区域 -->
    <div class="help-header">
      <div class="header-content">
        <div class="logo-area">
          <div class="logo-circle">
            <el-icon size="32" color="#3b82f6"><Document /></el-icon>
          </div>
          <div class="logo-text">
            <h1>帮助文档</h1>
            <p class="subtitle">云服务器管理系统 使用指南</p>
          </div>
        </div>
        
        <div class="search-area">
          <el-input
            v-model="searchKeyword"
            placeholder="搜索文档..."
            :prefix-icon="Search"
            class="search-input"
            clearable
            @input="handleSearch"
            @keyup.enter="handleSearch"
          >
            <template #append>
              <el-button :icon="Search" @click="handleSearch" />
            </template>
          </el-input>
        </div>
      </div>
    </div>

    <!-- 主内容区域 -->
    <div class="main-container">
      <!-- 左侧导航 -->
      <div class="side-nav" :class="{ 'nav-collapsed': navCollapsed }">
        <div class="nav-header">
          <span v-if="!navCollapsed">导航目录</span>
          <el-button 
            size="small" 
            circle 
            @click="navCollapsed = !navCollapsed"
            class="nav-toggle"
            :icon="navCollapsed ? 'ArrowRight' : 'ArrowLeft'"
          />
        </div>
        
        <div class="nav-content" v-show="!navCollapsed">
          <div 
            v-for="section in navigation" 
            :key="section.id"
            class="nav-section"
          >
            <div class="section-header" @click="toggleSection(section.id)">
              <div class="section-title">
                <el-icon><component :is="section.icon" /></el-icon>
                <span>{{ section.title }}</span>
              </div>
              <el-icon class="section-arrow">
                <ArrowDown v-if="expandedSections.includes(section.id)" />
                <ArrowRight v-else />
              </el-icon>
            </div>
            
            <el-collapse-transition>
              <div v-show="expandedSections.includes(section.id)" class="section-links">
                <div 
                  v-for="item in section.items" 
                  :key="item.id"
                  class="nav-link"
                  :class="{ active: activeNavId === item.id }"
                  @click="scrollToSection(item.id)"
                >
                  {{ item.title }}
                </div>
              </div>
            </el-collapse-transition>
          </div>
        </div>
      </div>

      <!-- 右侧文档内容 -->
      <div class="content-area">
        <div class="document-card">
          <!-- 系统概述 -->
          <section id="overview" class="doc-section">
            <div class="section-header">
              <div class="section-icon">
                <el-icon size="24"><InfoFilled /></el-icon>
              </div>
              <h2>系统概述</h2>
            </div>
            <div class="section-content">
              <div class="info-card">
                <p class="intro-text">
                  这是一个内部服务器管理系统，用于管理物理服务器、MV200服务器等资源以及测试用例自动化运行。
                  系统提供了一体化的资源管理、监控和运维能力。
                </p>
              </div>
            </div>
          </section>

          <!-- 快速开始 -->
          <section id="quickstart" class="doc-section">
            <div class="section-header">
              <div class="section-icon">
                <el-icon size="24"><MagicStick /></el-icon>
              </div>
              <h2>快速开始</h2>
            </div>
            <div class="section-content">
              <div class="step-guide">
                <div class="step-item">
                  <div class="step-content">
                    <h3>登录系统</h3>
                    <p>使用公司账号密码登录系统平台</p>
                  </div>
                </div>
                
              </div>
            </div>
          </section>

          <!-- 功能指南 -->
          <section id="guide" class="doc-section">
            <div class="section-header">
              <div class="section-icon">
                <el-icon size="24"><Tools /></el-icon>
              </div>
              <h2>功能使用指南</h2>
            </div>
            <div class="section-content">
              <!-- 服务器管理 -->
              <div class="function-card">
                <div class="function-header">
                  <h3>服务器管理</h3>
                  <el-tag type="primary" size="small">核心功能</el-tag>
                </div>
                <div class="function-content">
                  <div class="operation-grid">
                    <div class="operation-item">
                      <div class="operation-icon primary">
                        <el-icon><Plus /></el-icon>
                      </div>
                      <div class="operation-info">
                        <h4>纳管服务器</h4>
                        <p>将新服务器纳入管理</p>
                      </div>
                    </div>
                    <div class="operation-item">
                      <div class="operation-icon success">
                        <el-icon><Refresh /></el-icon>
                      </div>
                      <div class="operation-info">
                        <h4>冷/热重启</h4>
                        <p>服务器电源管理</p>
                      </div>
                    </div>
                    <div class="operation-item">
                      <div class="operation-icon info">
                        <el-icon><View /></el-icon>
                      </div>
                      <div class="operation-info">
                        <h4>查看详情</h4>
                        <p>查看服务器信息</p>
                      </div>
                    </div>
                    <div class="operation-item">
                      <div class="operation-icon warning">
                        <el-icon><Delete /></el-icon>
                      </div>
                      <div class="operation-info">
                        <h4>删除服务器</h4>
                        <p>移除服务器管理</p>
                      </div>
                    </div>
                    <div class="operation-item">
                      <div class="operation-icon primary">
                        <el-icon><Upload /></el-icon>
                      </div>
                      <div class="operation-info">
                        <h4>更新MCR</h4>
                        <p>将自动重启</p>
                      </div>
                    </div>
                    <div class="operation-item">
                      <div class="operation-icon success">
                        <el-icon><Setting /></el-icon>
                      </div>
                      <div class="operation-info">
                        <h4>修改启动项</h4>
                        <p>配置启动顺序</p>
                      </div>
                    </div>
                    <div class="operation-item">
                      <div class="operation-icon warning">
                        <el-icon><Lock /></el-icon>
                      </div>
                      <div class="operation-info">
                        <h4>占用服务器</h4>
                        <p>标记使用状态</p>
                      </div>
                    </div>
                    <div class="operation-item">
                      <div class="operation-icon info">
                        <el-icon><Unlock /></el-icon>
                      </div>
                      <div class="operation-info">
                        <h4>释放服务器</h4>
                        <p>解除占用状态</p>
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              <div class="function-card">
                <div class="function-header">
                  <h3>MV200管理</h3>
                  <el-tag type="success" size="small">mv200</el-tag>
                </div>
                <div class="function-content">
                  <div class="operation-grid">
                    <div class="operation-item">
                      <div class="operation-icon primary">
                        <el-icon><Plus /></el-icon>
                      </div>
                      <div class="operation-info">
                        <h4>纳管MV200</h4>
                        <p>将MV200纳入管理</p>
                      </div>
                    </div>
                    <div class="operation-item">
                      <div class="operation-icon success">
                        <el-icon><Refresh /></el-icon>
                      </div>
                      <div class="operation-info">
                        <h4>调整MV200恢复模式</h4>
                        <p>自动/手动恢复</p>
                      </div>
                    </div>
                    <div class="operation-item">
                      <div class="operation-icon info">
                        <el-icon><View /></el-icon>
                      </div>
                      <div class="operation-info">
                        <h4>查看详情</h4>
                        <p>查看MV200信息</p>
                      </div>
                    </div>
                    <div class="operation-item">
                      <div class="operation-icon warning">
                        <el-icon><Delete /></el-icon>
                      </div>
                      <div class="operation-info">
                        <h4>删除MV200</h4>
                        <p>移除MV200</p>
                      </div>
                    </div>
                    <div class="operation-item">
                      <div class="operation-icon primary">
                        <el-icon><Upload /></el-icon>
                      </div>
                      <div class="operation-info">
                        <h4>更新MCR</h4>
                        <p>需要手动冷重启</p>
                      </div>
                    </div>
                    <div class="operation-item">
                      <div class="operation-icon success">
                        <el-icon><Setting /></el-icon>
                      </div>
                      <div class="operation-info">
                        <h4>调整MV200启动模式</h4>
                        <p>云盘/非云盘启动</p>
                      </div>
                    </div>

                    <div class="operation-item">
                    <div class="operation-icon primary">
                        <el-icon><DataBoard /></el-icon>
                    </div>
                    <div class="operation-info">
                        <h4>云系统盘管理</h4>
                        <p>创建/删除云系统盘</p>
                    </div>
                    </div>
                    <div class="operation-item">
                    <div class="operation-icon success">
                        <el-icon><Connection /></el-icon>
                    </div>
                    <div class="operation-info">
                        <h4>XSC网口管理</h4>
                        <p>创建/删除XSC网口</p>
                    </div>
                    </div>
                  </div>
                </div>
              </div>

                <!-- 质量保证平台 -->
                <div class="function-card">
                <div class="function-header">
                    <h3>质量保证平台</h3>
                    <el-tag type="warning" size="small">测试管理</el-tag>
                </div>
                <div class="function-content">
                    <div class="operation-grid">
                    <div class="operation-item">
                        <div class="operation-icon primary">
                        <el-icon><Switch /></el-icon>
                        </div>
                        <div class="operation-info">
                        <h4>切换测试分支/标签</h4>
                        <p>选择测试代码版本</p>
                        </div>
                    </div>
                    <div class="operation-item">
                        <div class="operation-icon success">
                        <el-icon><Search /></el-icon>
                        </div>
                        <div class="operation-info">
                        <h4>扫描测试用例</h4>
                        <p>发现可用测试用例</p>
                        </div>
                    </div>
                    <div class="operation-item">
                        <div class="operation-icon info">
                        <el-icon><VideoPlay /></el-icon>
                        </div>
                        <div class="operation-info">
                        <h4>执行测试用例</h4>
                        <p>运行选择的测试</p>
                        </div>
                    </div>
                    <div class="operation-item">
                        <div class="operation-icon warning">
                        <el-icon><Histogram /></el-icon>
                        </div>
                        <div class="operation-info">
                        <h4>查看测试历史</h4>
                        <p>查看执行结果详情</p>
                        </div>
                    </div>
                    </div>
                </div>
                </div>



              <!-- 操作审计 -->
              <div class="function-card">
                <div class="function-header">
                  <h3>操作审计</h3>
                  <el-tag type="info" size="small">安全监控</el-tag>
                </div>
                <div class="function-content">
                  <el-descriptions :column="2" border>
                    <el-descriptions-item label="实时监控">
                      记录所有关键操作
                    </el-descriptions-item>
                    <el-descriptions-item label="多维筛选">
                      按用户、时间筛选
                    </el-descriptions-item>
                    <el-descriptions-item label="状态追踪">
                      查看操作执行结果
                    </el-descriptions-item>
                    <el-descriptions-item label="导出功能">
                      暂不支持
                    </el-descriptions-item>
                  </el-descriptions>
                </div>
              </div>
            </div>
          </section>

          <!-- 常见问题 -->
          <section id="faq" class="doc-section">
            <div class="section-header">
              <div class="section-icon">
                <el-icon size="24"><QuestionFilled /></el-icon>
              </div>
              <h2>常见问题</h2>
            </div>
            <div class="section-content">
              <div class="faq-list">
                <el-collapse v-model="activeFaq">
                  <el-collapse-item name="faq1" title="SSH登录后占用提示信息与实际不符？">
                    <div class="faq-content">
                      <p><strong>问题原因：</strong></p>
                      <ol>
                        <li>占用/释放时，服务器的操作系统与当前操作系统不一致。</li>
                        <li>系统仅更新占用/释放时的操作系统内的提示信息</li>
                      </ol>
                      <p><strong>解决方案：</strong></p>
                      <ul>
                        <li>实际占用情况以本平台服务器列表的信息为准</li>
                        <li>在当前操作系统再次进行占用/释放操作以刷新当前系统的提示</li>
                      </ul>
                    </div>
                  </el-collapse-item>
                  
                  <el-collapse-item name="faq2" title="冷/热重启服务器失败？">
                    <div class="faq-content">
                      <p><strong>可能原因：</strong></p>
                      <ul>
                        <li>管理平台与服务器的BMC IP地址不通且服务器离线</li>
                        <li>BMC的IPMI协议平台尚未兼容且服务器离线</li>
                      </ul>
                      <p><strong>解决方案：</strong></p>
                      <ul>
                        <li>等待离线的服务器在线后重试</li>
                        <li>登录服务器的BMC页面手动进行冷/热重启</li>
                      </ul>
                      
                      <p><strong>排查步骤：</strong></p>
                      <el-steps direction="vertical" :active="1">
                        <el-step title="检查BMC IP网络连通性" />
                        <el-step title="检查服务器 IP网络连通性" />
                      </el-steps>
                    </div>
                  </el-collapse-item>
                  
                  <el-collapse-item name="faq3" title="页面加载缓慢？">
                    <div class="faq-content">
                      <p><strong>优化建议：</strong></p>
                      <div class="suggestion-grid">
                        <div class="suggestion-item">
                          <el-icon><Delete /></el-icon>
                          <span>清理浏览器缓存</span>
                        </div>
                        <div class="suggestion-item">
                          <el-icon><Connection /></el-icon>
                          <span>检查网络连接</span>
                        </div>
                        <div class="suggestion-item">
                          <el-icon><Close /></el-icon>
                          <span>减少打开的页面</span>
                        </div>
                      </div>
                    </div>
                  </el-collapse-item>
                </el-collapse>
              </div>
            </div>
          </section>

          <!-- 版本历史 -->
          <section id="changelog" class="doc-section">
            <div class="section-header">
              <div class="section-icon">
                <el-icon size="24"><Histogram /></el-icon>
              </div>
              <h2>版本更新历史</h2>
            </div>
            <div class="section-content">
              <div class="timeline">
                <div class="timeline-item">
                  <div class="timeline-date">
                    <span class="date">2025-12-26</span>
                    <el-tag type="success" size="small">v2.0.4</el-tag>
                  </div>
                  <div class="timeline-content">
                    <div class="update-card">
                      <div class="update-type">
                        <el-tag type="success" size="small">新增功能</el-tag>
                      </div>
                      <ul>
                        <li>支持安装、启动lldpd，查询交换机信息</li>
                        <li>支持执行用例时自动添加网口上行信息</li>
                        <li>支持解析测试任务的执行结果并展示</li>
                        <li>支持查询服务器上网卡设备的pcie宽度及网口的ipv4/ipv6地址</li>
                        <li>支持服务器、mv200、云系统盘、xsc网口等资源的操作审计，参见[更多]-[操作日志]页面</li>
                      </ul>
                      <div class="update-type">
                        <el-tag type="warning" size="small">功能优化</el-tag>
                      </div>
                      <ul>
                        <li>优化服务器网口信息重复检测</li>
                      </ul>
                      <div class="update-type">
                        <el-tag type="info" size="small">问题修复</el-tag>
                      </div>
                      <ul>
                        <li>修复服务器信息中包含纯数字时，搜索功能异常的问题</li>
                      </ul>
                    </div>
                  </div>
                </div>
                
                <div class="timeline-item">
                  <div class="timeline-date">
                    <span class="date">2025-12-19</span>
                    <el-tag type="primary" size="small">v2.0.3</el-tag>
                  </div>
                  <div class="timeline-content">
                    <div class="update-card">
                      <div class="update-type">
                        <el-tag type="success" size="small">新增功能</el-tag>
                      </div>
                      <ul>
                        <li>增加服务器占用的飞书提醒及邮件提醒</li>
                      </ul>
                      <div class="update-type">
                        <el-tag type="warning" size="small">功能优化</el-tag>
                      </div>
                      <ul>
                        <li>质量保证平台运行测试用例前自动拉取最新测试代码</li>
                        <li>服务器列表改为分页显示</li>
                        <li>优化重启服务器流程：如果远程ipmitool执行失败(ipmi网络不通等)时尝试ssh到服务器上本地执行冷/热重启命令</li>
                        <li>改进MCR更新流程：优先执行./install.sh --force，如果失败则执行./uninstall --force后再./install.sh --force</li>
                      </ul>
                       <div class="update-type">
                        <el-tag type="info" size="small">问题修复</el-tag>
                      </div>
                      <ul>
                        <li>修复通过非本平台对mv200的自动恢复模式进行修改后，本平台无法再下发修改模式请求的问题</li>
                        <li>修复测试代码的branch/tag在gitlab仓库删除导致本平台无法再切换到"质量保证平台"页面的问题</li>
                      </ul>
                    </div>
                  </div>
                </div>

                <div class="timeline-item">
                  <div class="timeline-date">
                    <span class="date">2025-12-12</span>
                    <el-tag type="primary" size="small">v2.0.2</el-tag>
                  </div>
                  <div class="timeline-content">
                    <div class="update-card">
                      <div class="update-type">
                        <el-tag type="success" size="small">新增功能</el-tag>
                      </div>
                      <ul>
                        <li>支持根据 tag、网卡类型、关注来筛选服务器，并记录筛选条件，下次默认应用</li>
                        <li>支持检索服务器 GRUB 信息并在服务器详情页面展示</li>
                        <li>支持纳管没有安装驱动的服务器（但需要有 `yuncli` 才能正确获取完整网卡信息）</li>
                        <li>支持扫描服务器上 Mellanox 网卡</li>
                        <li>支持提醒邮件分组发送：系统设置页面允许为标签添加自定义 webhook 飞书机器人，服务器添加该标签时，释放提示消息会发送至对应飞书群</li>
                      </ul>
                      <div class="update-type">
                        <el-tag type="warning" size="small">功能优化</el-tag>
                      </div>
                      <ul>
                        <li>切换到[质量保证平台]页面时自动拉取当前分支最新代码</li>
                        <li>服务器详情页面自动获取最新板卡信息与启动项信息，不再需要手动点击更新</li>
                        <li>纳管服务器时自动配置 yum/apt源(已支持centos7/8/ubuntu)，安装依赖包</li>
                        <li>允许提前取消后台测试任务, 生成已执行测试用例的测试报告</li>
                        <li>优化云脉网卡扫描：需要结合lspci以及yuncli获取到的fru来识别所有网卡及板卡类型 </li>
                      </ul>
                       <div class="update-type">
                        <el-tag type="info" size="small">问题修复</el-tag>
                      </div>
                      <ul>
                        <li>修复平台重启时会中断后台测试任务，重启后任务状态始终为运行中，无法取消的问题</li>
                        <li>修复部分服务器获取启动项失败（部分老系统 `lsblk` 命令没有 PTTYPE）的问题</li>
                        <li>修复编辑服务器信息会导致占用信息丢失的问题</li>
                      </ul>
                    </div>
                  </div>
                </div>

                <div class="timeline-item">
                  <div class="timeline-date">
                    <span class="date">2025-12-05</span>
                    <el-tag type="primary" size="small">v2.0.1</el-tag>
                  </div>
                  <div class="timeline-content">
                    <div class="update-card">
                      <div class="update-type">
                        <el-tag type="success" size="small">新增功能</el-tag>
                      </div>
                      <ul>
                        <li>支持执行测试用例</li>
                        <li>支持查看用例执行历史，展示执行日志、yaml env，集成allure测试结果页面</li>
                        <li>支持用户自定义用例集合，允许共享集合</li>
                        <li>支持执行测试用例时选用mv200，并生成对应的yaml env文件</li>
                      </ul>
                      <div class="update-type">
                        <el-tag type="warning" size="small">功能优化</el-tag>
                      </div>
                      <ul>
                        <li>完善服务器管理页面的mcr包更新功能，支持自动安装任务所需的工具，监测更新状态</li>
                      </ul>
                    </div>
                  </div>
                </div>

                <div class="timeline-item">
                  <div class="timeline-date">
                    <span class="date">2025-11-28</span>
                    <el-tag type="primary" size="small">v2.0.0</el-tag>
                  </div>
                  <div class="timeline-content">
                    <div class="update-card">
                      <div class="update-type">
                        <el-tag type="success" size="small">新增功能</el-tag>
                      </div>
                      <ul>
                        <li>支持关注服务器：服务器占用释放时使用飞书及邮箱提醒关注人</li>
                        <li>支持检索服务器impi的地址</li>
                        <li>支持更新服务器MCR包，并展示更新结果</li>
                      </ul>
                      <div class="update-type">
                        <el-tag type="warning" size="small">功能优化</el-tag>
                      </div>
                      <ul>
                        <li>更换质量保证平台后台对接的测试框架为yuntester</li>
                      </ul>
                    </div>
                  </div>
                </div>

                <div class="timeline-item">
                  <div class="timeline-date">
                    <span class="date">2025-XX-XX</span>
                    <el-tag type="primary" size="small">v1.0.0</el-tag>
                  </div>
                  <div class="timeline-content">
                    <div class="update-card">
                      <div class="update-type">
                        <el-tag type="success" size="small">新增功能</el-tag>
                      </div>
                      <ul>
                        <li>云服务器管理平台改造及新增【质量保证平台】页面</li>
                      </ul>
                    </div>
                  </div>
                </div>

              </div>
            </div>
          </section>

          <!-- 技术支持 -->
          <section id="support" class="doc-section">
            <div class="section-header">
              <div class="section-icon">
                <el-icon size="24"><Service /></el-icon>
              </div>
              <h2>支持人员</h2>
            </div>
            <div class="section-content">
              <div class="support-grid">
                
                <div class="support-card">
                  <div class="support-icon">
                    <el-icon><ChatDotRound /></el-icon>
                  </div>
                  <div class="support-info">
                    <h4>平台功能问题</h4>
                    <p>飞书联系"吴柏林"</p>
                  </div>
                </div>

                <div class="support-card">
                  <div class="support-icon">
                    <el-icon><ChatDotRound /></el-icon>
                  </div>
                  <div class="support-info">
                    <h4>测试框架及用例问题</h4>
                    <p>飞书联系"邹郁/赵智聪/陈昱竹/陈轩"</p>
                  </div>
                </div>

              </div>
              
              <div class="footer-note">
                <p class="note-text">
                  <el-icon><InfoFilled /></el-icon>
                  本文档会根据系统更新而调整，请关注最新版本信息
                </p>
                <p class="update-info">
                  <span>最后更新：2025年12月26日</span>
                  <span>当前版本：v1.2.0</span>
                </p>
              </div>
            </div>
          </section>
        </div>
      </div>
    </div>

    <!-- 操作按钮 -->
    <div class="action-buttons">
      <el-button 
        type="primary" 
        circle 
        size="large"
        @click="scrollToTop"
        v-show="showScrollTop"
        class="scroll-top-btn"
      >
        <el-icon><Top /></el-icon>
      </el-button>
      <el-tooltip content="打印文档" placement="left">
        <el-button 
          type="info" 
          circle 
          size="large"
          @click="printDocument"
          class="print-btn"
        >
          <el-icon><Printer /></el-icon>
        </el-button>
      </el-tooltip>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import { ElMessage } from 'element-plus'
import {
  // 图标
  Document, Search, ArrowLeft, ArrowRight, ArrowDown,
  InfoFilled, MagicStick, Tools, QuestionFilled,
  Histogram, Service, Top, Printer, VideoPlay,
  Monitor, Cpu, Check, DocumentChecked, Setting,
  DataAnalysis, View, Delete, Upload, Refresh,
  Lock, Unlock, Plus, DataBoard, Connection, Switch,
  User, ChatDotRound, Clock, Warning, Close
} from '@element-plus/icons-vue'

// 状态管理
const searchKeyword = ref('')
const navCollapsed = ref(false)
const expandedSections = ref<string[]>(['guide', 'faq'])
const activeNavId = ref('overview')
const activeFaq = ref(['faq1'])
const showScrollTop = ref(false)

// 导航数据
const navigation = ref([
  {
    id: 'overview',
    title: '系统概述',
    icon: 'InfoFilled',
    items: [
      { id: 'overview', title: '系统简介' }
    ]
  },
  {
    id: 'quickstart',
    title: '快速开始',
    icon: 'MagicStick',
    items: [
      { id: 'quickstart', title: '入门指南' }
    ]
  },
  {
    id: 'guide',
    title: '功能指南',
    icon: 'Tools',
    items: [
      { id: 'guide', title: '服务器管理' },
      { id: 'guide', title: 'MV200管理' },
      { id: 'guide', title: '质量保证平台' },
      { id: 'guide', title: '操作审计' }
    ]
  },
  {
    id: 'faq',
    title: '常见问题',
    icon: 'QuestionFilled',
    items: [
      { id: 'faq', title: '问题解答' }
    ]
  },
  {
    id: 'changelog',
    title: '版本历史',
    icon: 'Histogram',
    items: [
      { id: 'changelog', title: '更新记录' }
    ]
  },
  {
    id: 'support',
    title: '技术支持',
    icon: 'Service',
    items: [
      { id: 'support', title: '联系方式' }
    ]
  }
])

// 切换导航章节
const toggleSection = (sectionId: string) => {
  const index = expandedSections.value.indexOf(sectionId)
  if (index > -1) {
    expandedSections.value.splice(index, 1)
  } else {
    expandedSections.value.push(sectionId)
  }
}

// 滚动到指定章节
const scrollToSection = (sectionId: string) => {
  activeNavId.value = sectionId
  const element = document.getElementById(sectionId)
  if (element) {
    element.scrollIntoView({ 
      behavior: 'smooth',
      block: 'start'
    })
  }
}

// 滚动到顶部
const scrollToTop = () => {
  window.scrollTo({
    top: 0,
    behavior: 'smooth'
  })
}

// 搜索功能
const handleSearch = () => {
  const keyword = searchKeyword.value.trim().toLowerCase()
  if (!keyword) return
  
  // 这里可以添加搜索逻辑
  ElMessage.info({
    message: `尚未实现搜索`,
    duration: 2000
  })
}

// 打印文档
const printDocument = () => {
  setTimeout(() => {
    window.print()
  }, 500)
}

// 监听滚动
const handleScroll = () => {
  showScrollTop.value = window.pageYOffset > 400
  
  // 更新激活的导航项
  const sections = ['overview', 'quickstart', 'guide', 'faq', 'changelog', 'support']
  for (const section of sections) {
    const element = document.getElementById(section)
    if (element) {
      const rect = element.getBoundingClientRect()
      if (rect.top <= 100 && rect.bottom >= 100) {
        activeNavId.value = section
        break
      }
    }
  }
}

onMounted(() => {
  window.addEventListener('scroll', handleScroll)
})

onUnmounted(() => {
  window.removeEventListener('scroll', handleScroll)
})
</script>
<style scoped>
.help-page {
  min-height: 100vh;
  background: linear-gradient(135deg, #f8fafc 0%, #e5e7eb 100%);
}

/* 头部样式 */
.help-header {
  background: linear-gradient(135deg, #1e40af 0%, #3b82f6 100%);
  color: white;
  padding: 40px 0;
  position: relative;
  overflow: hidden;
}

.help-header::before {
  content: '';
  position: absolute;
  top: 0;
  right: 0;
  width: 300px;
  height: 300px;
  background: radial-gradient(circle, rgba(255, 255, 255, 0.1) 0%, transparent 70%);
  border-radius: 50%;
}

.header-content {
  max-width: 1400px;
  margin: 0 auto;
  padding: 0 40px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  position: relative;
  z-index: 1;
}

.logo-area {
  display: flex;
  align-items: center;
  gap: 20px;
}

.logo-circle {
  width: 64px;
  height: 64px;
  background: rgba(255, 255, 255, 0.1);
  backdrop-filter: blur(10px);
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  border: 2px solid rgba(255, 255, 255, 0.2);
}

.logo-text h1 {
  margin: 0;
  font-size: 32px;
  font-weight: 700;
  letter-spacing: -0.5px;
}

.subtitle {
  margin: 8px 0 0;
  opacity: 0.9;
  font-size: 16px;
}

.search-area {
  width: 400px;
}

.search-input {
  border-radius: 25px;
  overflow: hidden;
}

.search-input :deep(.el-input-group__append) {
  border-radius: 0 25px 25px 0;
}

/* 主内容区域 */
.main-container {
  margin: 20px auto 0;
  display: flex;
  gap: 24px;
}

/* 左侧导航 */
.side-nav {
  width: 280px;
  flex-shrink: 0;
  background: white;
  border-radius: 16px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.08);
  overflow: hidden;
  transition: all 0.3s ease;
}

.nav-collapsed {
  width: 60px;
}

.nav-header {
  padding: 24px;
  border-bottom: 1px solid #e5e7eb;
  display: flex;
  justify-content: space-between;
  align-items: center;
  background: linear-gradient(135deg, #f8fafc 0%, #e5e7eb 100%);
}

.nav-header span {
  font-weight: 600;
  color: #1f2937;
  font-size: 18px;
}

.nav-toggle {
  border: none;
  background: white;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.nav-content {
  padding: 16px 0;
}

.nav-section {
  border-bottom: 1px solid #f3f4f6;
}

/* 左侧导航的 section-header - 保持不变 */
.section-header {
  padding: 16px 24px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  cursor: pointer;
  transition: all 0.2s ease;
}

.section-header:hover {
  background: #f9fafb;
}

.section-title {
  display: flex;
  align-items: center;
  gap: 12px;
  font-weight: 500;
  color: #374151;
}

.section-arrow {
  color: #9ca3af;
  transition: transform 0.2s ease;
}

.section-links {
  padding: 8px 0 8px 64px;
}

.nav-link {
  padding: 12px 16px;
  margin: 4px 0;
  border-radius: 8px;
  cursor: pointer;
  color: #6b7280;
  font-size: 14px;
  transition: all 0.2s ease;
  position: relative;
}

.nav-link:hover {
  background: #f3f4f6;
  color: #374151;
}

.nav-link.active {
  background: #f0f9ff;
  color: #1d4ed8;
  font-weight: 500;
}

.nav-link.active::before {
  content: '';
  position: absolute;
  left: 0;
  top: 50%;
  transform: translateY(-50%);
  width: 3px;
  height: 16px;
  background: #3b82f6;
  border-radius: 0 2px 2px 0;
}

/* 右侧内容区域 */
.content-area {
  flex: 1;
}

.document-card {
  background: white;
  border-radius: 16px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.08);
  overflow: hidden;
}

.doc-section {
  padding: 48px;
  border-bottom: 1px solid #f3f4f6;
}

.doc-section:last-child {
  border-bottom: none;
}

/* 右侧文档内容的 section-header - 关键修复 */
.doc-section .section-header {
  display: flex;
  align-items: center;
  margin-bottom: 32px;
  width: 100%;
  flex-wrap: nowrap; /* 防止换行 */
}

/* 关键修复：给 section-icon 加上 .doc-section 前缀 */
.doc-section .section-icon {
  width: 56px;
  height: 56px;
  background: linear-gradient(135deg, #f0f9ff 0%, #dbeafe 100%);
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #3b82f6;
  flex-shrink: 0; /* 防止图标被压缩 */
  margin-right: 20px; /* 使用 margin-right 而不是 gap */
}

/* 关键修复：给 h2 加上 .doc-section 前缀 */
.doc-section .section-header h2 {
  margin: 0;
  font-size: 28px;
  font-weight: 700;
  color: #1f2937;
  flex: 1; /* 让标题占据剩余空间 */
  min-width: 0; /* 防止标题溢出 */
}

/* 系统概述样式 */
.intro-text {
  font-size: 18px;
  line-height: 1.8;
  color: #4b5563;
  margin-bottom: 40px;
}

.feature-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 24px;
}

.feature-item {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 20px;
  background: #f9fafb;
  border-radius: 12px;
  transition: all 0.3s ease;
  border: 1px solid #e5e7eb;
}

.feature-item:hover {
  transform: translateY(-4px);
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.1);
  border-color: #3b82f6;
}

.feature-icon {
  width: 48px;
  height: 48px;
  background: linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%);
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
}

.feature-text h4 {
  margin: 0 0 4px;
  font-size: 18px;
  font-weight: 600;
  color: #1f2937;
}

.feature-text p {
  margin: 0;
  color: #6b7280;
  font-size: 14px;
}

/* 快速开始样式 */
.step-guide {
  display: flex;
  flex-direction: column;
  gap: 32px;
}

.step-item {
  display: flex;
  gap: 24px;
}

.step-number {
  width: 48px;
  height: 48px;
  flex-shrink: 0;
  background: linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%);
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  font-size: 20px;
  font-weight: 600;
  box-shadow: 0 4px 12px rgba(59, 130, 246, 0.3);
}

.step-content {
  flex: 1;
}

.step-content h3 {
  margin: 0 0 8px;
  font-size: 22px;
  color: #1f2937;
}

.step-content p {
  margin: 0 0 16px;
  color: #6b7280;
  line-height: 1.6;
}

.step-tips {
  display: flex;
  align-items: center;
  gap: 8px;
  color: #6b7280;
  font-size: 14px;
}

.module-list {
  margin-top: 16px;
}

.module-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 16px;
  background: #f9fafb;
  border-radius: 12px;
  margin-bottom: 12px;
  transition: all 0.2s ease;
  border: 1px solid #e5e7eb;
}

.module-item:hover {
  background: #f0f9ff;
  border-color: #3b82f6;
}

.module-item .el-icon {
  color: #3b82f6;
  font-size: 18px;
}

.module-item span {
  font-weight: 500;
  color: #374151;
}

/* 功能指南样式 */
.function-card {
  margin-bottom: 40px;
  padding: 24px;
  background: #f9fafb;
  border-radius: 16px;
  border: 1px solid #e5e7eb;
}

.function-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
}

.function-header h3 {
  margin: 0;
  font-size: 24px;
  color: #1f2937;
}

.operation-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 20px;
}

.operation-item {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 16px;
  background: white;
  border-radius: 12px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
  transition: all 0.3s ease;
}

.operation-item:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.1);
}

.operation-icon {
  width: 48px;
  height: 48px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 20px;
  color: white;
}

.operation-icon.primary {
  background: linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%);
}

.operation-icon.success {
  background: linear-gradient(135deg, #10b981 0%, #059669 100%);
}

.operation-icon.info {
  background: linear-gradient(135deg, #06b6d4 0%, #0891b2 100%);
}

.operation-icon.warning {
  background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%);
}

.operation-info h4 {
  margin: 0 0 4px;
  font-size: 16px;
  font-weight: 600;
  color: #1f2937;
}

.operation-info p {
  margin: 0;
  color: #6b7280;
  font-size: 13px;
}

.mv200-features .feature-row {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 32px;
}

.feature-col {
  display: flex;
  align-items: center;
  gap: 16px;
}

.feature-col .el-icon {
  font-size: 32px;
  color: #3b82f6;
}

.feature-col h4 {
  margin: 0 0 4px;
  font-size: 18px;
  color: #1f2937;
}

.feature-col p {
  margin: 0;
  color: #6b7280;
  font-size: 14px;
}

/* 常见问题样式 */
.faq-content {
  padding: 8px;
}

.faq-content p {
  margin: 12px 0;
  line-height: 1.6;
  color: #4b5563;
}

.faq-content ol,
.faq-content ul {
  margin: 16px 0;
  padding-left: 24px;
}

.faq-content li {
  margin: 8px 0;
  color: #4b5563;
}

.suggestion-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
  margin-top: 16px;
}

.suggestion-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px;
  background: #f9fafb;
  border-radius: 8px;
  border: 1px solid #e5e7eb;
}

.suggestion-item .el-icon {
  color: #3b82f6;
}

.suggestion-item span {
  font-size: 14px;
  color: #374151;
}

/* 版本历史样式 */
.timeline {
  position: relative;
  padding-left: 24px;
}

.timeline::before {
  content: '';
  position: absolute;
  left: 0;
  top: 0;
  bottom: 0;
  width: 2px;
  background: linear-gradient(to bottom, #3b82f6, #10b981, #f59e0b);
}

.timeline-item {
  position: relative;
  margin-bottom: 32px;
}

.timeline-item:last-child {
  margin-bottom: 0;
}

.timeline-item::before {
  content: '';
  position: absolute;
  left: -30px;
  top: 8px;
  width: 12px;
  height: 12px;
  border-radius: 50%;
  background: #3b82f6;
  border: 3px solid white;
  box-shadow: 0 0 0 3px #dbeafe;
}

.timeline-date {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 12px;
}

.timeline-date .date {
  font-size: 18px;
  font-weight: 600;
  color: #1f2937;
}

.update-card {
  padding: 20px;
  background: #f9fafb;
  border-radius: 12px;
  border: 1px solid #e5e7eb;
}

.update-type {
  margin: 16px 0 8px;
}

.update-type:first-child {
  margin-top: 0;
}

.update-card ul {
  margin: 0;
  padding-left: 20px;
}

.update-card li {
  margin: 6px 0;
  color: #4b5563;
  line-height: 1.5;
}

/* 技术支持样式 */
.support-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 20px;
  margin-bottom: 40px;
}

.support-card {
  display: flex;
  align-items: center;
  gap: 20px;
  padding: 24px;
  background: #f9fafb;
  border-radius: 16px;
  border: 1px solid #e5e7eb;
  transition: all 0.3s ease;
}

.support-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
  border-color: #3b82f6;
}

.support-icon {
  width: 56px;
  height: 56px;
  background: linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%);
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  font-size: 24px;
}

.support-info h4 {
  margin: 0 0 4px;
  font-size: 18px;
  color: #1f2937;
}

.support-info p {
  margin: 0;
  color: #6b7280;
  font-size: 16px;
}

.footer-note {
  padding: 24px;
  background: linear-gradient(135deg, #f0f9ff 0%, #dbeafe 100%);
  border-radius: 16px;
  border: 1px solid #dbeafe;
}

.note-text {
  display: flex;
  align-items: center;
  gap: 12px;
  margin: 0 0 16px;
  color: #1e40af;
  font-size: 16px;
  font-weight: 500;
}

.update-info {
  display: flex;
  justify-content: space-between;
  color: #6b7280;
  font-size: 14px;
}

/* 操作按钮 */
.action-buttons {
  position: fixed;
  right: 40px;
  bottom: 40px;
  display: flex;
  flex-direction: column;
  gap: 16px;
  z-index: 100;
}

.scroll-top-btn {
  background: linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%);
  border: none;
  box-shadow: 0 4px 16px rgba(59, 130, 246, 0.4);
}

.print-btn {
  background: linear-gradient(135deg, #6b7280 0%, #4b5563 100%);
  border: none;
  box-shadow: 0 4px 16px rgba(107, 114, 128, 0.4);
}

/* 响应式设计 */
@media (max-width: 1200px) {
  .main-container {
    flex-direction: column;
  }
  
  .side-nav {
    width: 100%;
  }
  
  .nav-collapsed {
    width: 100%;
    height: auto;
  }
  
  .operation-grid {
    grid-template-columns: repeat(2, 1fr);
  }
  
  .support-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 768px) {
  .header-content {
    flex-direction: column;
    gap: 24px;
    text-align: center;
  }
  
  .search-area {
    width: 100%;
  }
  
  .main-container {
    padding: 0 20px 40px;
  }
  
  .doc-section {
    padding: 32px 24px;
  }
  
  .feature-grid {
    grid-template-columns: 1fr;
  }
  
  .mv200-features .feature-row {
    grid-template-columns: 1fr;
    gap: 24px;
  }
  
  .operation-grid {
    grid-template-columns: 1fr;
  }
  
  .step-item {
    flex-direction: column;
  }
  
  .step-number {
    align-self: flex-start;
  }
  
  .update-info {
    flex-direction: column;
    gap: 8px;
  }
  
  .action-buttons {
    right: 20px;
    bottom: 20px;
  }
}

/* 打印优化 */
@media print {
  .help-header {
    background: white !important;
    color: black !important;
    padding: 20px 0;
  }
  
  .logo-circle {
    background: #f3f4f6 !important;
    border-color: #d1d5db !important;
  }
  
  .logo-text h1 {
    color: black !important;
  }
  
  .subtitle {
    color: #6b7280 !important;
  }
  
  .search-area,
  .side-nav,
  .action-buttons,
  .nav-toggle,
  .el-collapse-item__header .el-icon,
  .section-arrow {
    display: none !important;
  }
  
  .main-container {
    margin: 0;
    padding: 0;
  }
  
  .document-card {
    box-shadow: none !important;
  }
  
  .feature-item,
  .function-card,
  .support-card,
  .update-card {
    break-inside: avoid;
    box-shadow: none !important;
    border: 1px solid #d1d5db !important;
  }
  
  .footer-note {
    background: #f3f4f6 !important;
    border-color: #d1d5db !important;
  }
}
</style>