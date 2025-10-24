// Employee Management System - Main Application JavaScript
// A Square Skills Academy EMS

class EMSApp {
  constructor() {
    this.apiBase = '/api/v1';
    this.currentUser = null;
    this.token = null;
    this.init();
  }

  init() {
    this.setupEventListeners();
    this.checkAuthStatus();
    this.initializeTheme();
  }

  // Authentication
  async login(email, password, rememberMe = false) {
    try {
      const response = await fetch(`${this.apiBase}/auth/login`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ email, password, remember_me: rememberMe }),
      });

      const data = await response.json();

      if (response.ok) {
        this.currentUser = data.user;
        this.token = data.access_token;
        this.redirectToDashboard();
      } else {
        this.showAlert(data.detail || 'Login failed', 'danger');
      }
    } catch (error) {
      console.error('Login error:', error);
      this.showAlert('Network error. Please try again.', 'danger');
    }
  }

  async logout() {
    try {
      await fetch(`${this.apiBase}/auth/logout`, {
        method: 'POST',
        headers: this.getAuthHeaders(),
      });
    } catch (error) {
      console.error('Logout error:', error);
    } finally {
      this.clearAuth();
      this.redirectToLogin();
    }
  }

  clearAuth() {
    this.currentUser = null;
    this.token = null;
    document.cookie = 'access_token=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;';
    document.cookie = 'refresh_token=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;';
  }

  getAuthHeaders() {
    return {
      'Authorization': `Bearer ${this.token}`,
      'Content-Type': 'application/json',
    };
  }

  async checkAuthStatus() {
    const token = this.getCookie('access_token');
    if (token) {
      this.token = token;
      try {
        const response = await fetch(`${this.apiBase}/auth/me`, {
          headers: this.getAuthHeaders(),
        });
        
        if (response.ok) {
          this.currentUser = await response.json();
          this.updateUI();
        } else {
          this.clearAuth();
        }
      } catch (error) {
        console.error('Auth check error:', error);
        this.clearAuth();
      }
    }
  }

  // UI Components
  showAlert(message, type = 'info', duration = 5000) {
    const alert = document.createElement('div');
    alert.className = `alert alert-${type}`;
    alert.textContent = message;
    
    const container = document.querySelector('.alert-container') || document.body;
    container.insertBefore(alert, container.firstChild);
    
    setTimeout(() => {
      alert.remove();
    }, duration);
  }

  showLoading(element) {
    element.innerHTML = '<span class="loading"></span> Loading...';
    element.disabled = true;
  }

  hideLoading(element, originalText) {
    element.innerHTML = originalText;
    element.disabled = false;
  }

  // Theme Management
  initializeTheme() {
    const savedTheme = localStorage.getItem('theme') || 'light';
    this.setTheme(savedTheme);
  }

  setTheme(theme) {
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem('theme', theme);
  }

  toggleTheme() {
    const currentTheme = document.documentElement.getAttribute('data-theme');
    const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
    this.setTheme(newTheme);
  }

  // Navigation
  redirectToLogin() {
    window.location.href = '/index.html';
  }

  redirectToDashboard() {
    if (this.currentUser?.role === 'admin') {
      window.location.href = '/admin/dashboard.html';
    } else {
      window.location.href = '/employee/dashboard.html';
    }
  }

  // Utility Functions
  getCookie(name) {
    const value = `; ${document.cookie}`;
    const parts = value.split(`; ${name}=`);
    if (parts.length === 2) return parts.pop().split(';').shift();
  }

  formatDate(dateString) {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
    });
  }

  formatTime(dateString) {
    return new Date(dateString).toLocaleTimeString('en-US', {
      hour: '2-digit',
      minute: '2-digit',
    });
  }

  formatCurrency(amount) {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
    }).format(amount);
  }

  // Event Listeners
  setupEventListeners() {
    // Theme toggle
    document.addEventListener('click', (e) => {
      if (e.target.matches('[data-theme-toggle]')) {
        this.toggleTheme();
      }
    });

    // Logout
    document.addEventListener('click', (e) => {
      if (e.target.matches('[data-logout]')) {
        e.preventDefault();
        this.logout();
      }
    });

    // Form submissions
    document.addEventListener('submit', (e) => {
      if (e.target.matches('#loginForm')) {
        e.preventDefault();
        this.handleLogin(e.target);
      }
    });

    // Mobile menu toggle
    document.addEventListener('click', (e) => {
      if (e.target.matches('[data-mobile-menu-toggle]')) {
        this.toggleMobileMenu();
      }
    });
  }

  async handleLogin(form) {
    const formData = new FormData(form);
    const email = formData.get('email');
    const password = formData.get('password');
    const rememberMe = formData.get('rememberMe') === 'on';
    
    const submitBtn = form.querySelector('button[type="submit"]');
    const originalText = submitBtn.textContent;
    
    this.showLoading(submitBtn);
    
    await this.login(email, password, rememberMe);
    
    this.hideLoading(submitBtn, originalText);
  }

  toggleMobileMenu() {
    const sidebar = document.querySelector('.sidebar');
    sidebar.classList.toggle('open');
  }

  updateUI() {
    // Update user name in UI
    const userNameElements = document.querySelectorAll('[data-user-name]');
    userNameElements.forEach(el => {
      el.textContent = this.currentUser?.name || 'User';
    });

    // Update user role
    const userRoleElements = document.querySelectorAll('[data-user-role]');
    userRoleElements.forEach(el => {
      el.textContent = this.currentUser?.role || '';
    });

    // Show/hide admin-only elements
    const adminOnlyElements = document.querySelectorAll('[data-admin-only]');
    adminOnlyElements.forEach(el => {
      el.style.display = this.currentUser?.role === 'admin' ? 'block' : 'none';
    });
  }
}

// API Service Classes
class EmployeeService {
  constructor(app) {
    this.app = app;
  }

  async getAll(page = 1, limit = 10) {
    const response = await fetch(`${this.app.apiBase}/employees?page=${page}&limit=${limit}`, {
      headers: this.app.getAuthHeaders(),
    });
    return response.json();
  }

  async getById(id) {
    const response = await fetch(`${this.app.apiBase}/employees/${id}`, {
      headers: this.app.getAuthHeaders(),
    });
    return response.json();
  }

  async create(data) {
    const response = await fetch(`${this.app.apiBase}/employees`, {
      method: 'POST',
      headers: this.app.getAuthHeaders(),
      body: JSON.stringify(data),
    });
    return response.json();
  }

  async update(id, data) {
    const response = await fetch(`${this.app.apiBase}/employees/${id}`, {
      method: 'PUT',
      headers: this.app.getAuthHeaders(),
      body: JSON.stringify(data),
    });
    return response.json();
  }

  async delete(id) {
    const response = await fetch(`${this.app.apiBase}/employees/${id}`, {
      method: 'DELETE',
      headers: this.app.getAuthHeaders(),
    });
    return response.json();
  }
}

class TaskService {
  constructor(app) {
    this.app = app;
  }

  async getAll(status = null, assignedTo = null) {
    let url = `${this.app.apiBase}/tasks`;
    const params = new URLSearchParams();
    if (status) params.append('status', status);
    if (assignedTo) params.append('assigned_to', assignedTo);
    if (params.toString()) url += `?${params.toString()}`;

    const response = await fetch(url, {
      headers: this.app.getAuthHeaders(),
    });
    return response.json();
  }

  async create(data) {
    const response = await fetch(`${this.app.apiBase}/tasks`, {
      method: 'POST',
      headers: this.app.getAuthHeaders(),
      body: JSON.stringify(data),
    });
    return response.json();
  }

  async update(id, data) {
    const response = await fetch(`${this.app.apiBase}/tasks/${id}`, {
      method: 'PUT',
      headers: this.app.getAuthHeaders(),
      body: JSON.stringify(data),
    });
    return response.json();
  }

  async markComplete(id) {
    const response = await fetch(`${this.app.apiBase}/tasks/${id}/complete`, {
      method: 'PUT',
      headers: this.app.getAuthHeaders(),
    });
    return response.json();
  }
}

class AttendanceService {
  constructor(app) {
    this.app = app;
  }

  async getAll(userId = null, dateFrom = null, dateTo = null) {
    let url = `${this.app.apiBase}/attendance`;
    const params = new URLSearchParams();
    if (userId) params.append('user_id', userId);
    if (dateFrom) params.append('date_from', dateFrom);
    if (dateTo) params.append('date_to', dateTo);
    if (params.toString()) url += `?${params.toString()}`;

    const response = await fetch(url, {
      headers: this.app.getAuthHeaders(),
    });
    return response.json();
  }

  async startSession() {
    const response = await fetch(`${this.app.apiBase}/attendance/start`, {
      method: 'POST',
      headers: this.app.getAuthHeaders(),
    });
    return response.json();
  }

  async endSession() {
    const response = await fetch(`${this.app.apiBase}/attendance/end`, {
      method: 'POST',
      headers: this.app.getAuthHeaders(),
    });
    return response.json();
  }
}

class LeaveService {
  constructor(app) {
    this.app = app;
  }

  async getAll(status = null) {
    let url = `${this.app.apiBase}/leaves`;
    const params = new URLSearchParams();
    if (status) params.append('status', status);
    if (params.toString()) url += `?${params.toString()}`;

    const response = await fetch(url, {
      headers: this.app.getAuthHeaders(),
    });
    return response.json();
  }

  async apply(data) {
    const response = await fetch(`${this.app.apiBase}/leaves`, {
      method: 'POST',
      headers: this.app.getAuthHeaders(),
      body: JSON.stringify(data),
    });
    return response.json();
  }

  async approve(id) {
    const response = await fetch(`${this.app.apiBase}/leaves/${id}/approve`, {
      method: 'PUT',
      headers: this.app.getAuthHeaders(),
    });
    return response.json();
  }

  async reject(id, reason = '') {
    const response = await fetch(`${this.app.apiBase}/leaves/${id}/reject`, {
      method: 'PUT',
      headers: this.app.getAuthHeaders(),
      body: JSON.stringify({ reason }),
    });
    return response.json();
  }
}

class MessageService {
  constructor(app) {
    this.app = app;
  }

  async getConversations() {
    const response = await fetch(`${this.app.apiBase}/messages/conversations`, {
      headers: this.app.getAuthHeaders(),
    });
    return response.json();
  }

  async getMessages(userId) {
    const response = await fetch(`${this.app.apiBase}/messages/${userId}`, {
      headers: this.app.getAuthHeaders(),
    });
    return response.json();
  }

  async sendMessage(receiverId, message) {
    const response = await fetch(`${this.app.apiBase}/messages`, {
      method: 'POST',
      headers: this.app.getAuthHeaders(),
      body: JSON.stringify({ receiver_id: receiverId, message }),
    });
    return response.json();
  }
}

class ReportService {
  constructor(app) {
    this.app = app;
  }

  async generate(type, filters = {}) {
    const params = new URLSearchParams({ type, ...filters });
    const response = await fetch(`${this.app.apiBase}/reports?${params.toString()}`, {
      headers: this.app.getAuthHeaders(),
    });
    return response.json();
  }

  async export(format = 'pdf', type, filters = {}) {
    const params = new URLSearchParams({ format, type, ...filters });
    const response = await fetch(`${this.app.apiBase}/reports/export?${params.toString()}`, {
      headers: this.app.getAuthHeaders(),
    });
    
    if (response.ok) {
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `report_${type}_${new Date().toISOString()}.${format}`;
      a.click();
      window.URL.revokeObjectURL(url);
    }
  }
}

// Initialize the application
const app = new EMSApp();

// Export services for use in other files
window.EmployeeService = EmployeeService;
window.TaskService = TaskService;
window.AttendanceService = AttendanceService;
window.LeaveService = LeaveService;
window.MessageService = MessageService;
window.ReportService = ReportService;

// Make app instance globally available
window.emsApp = app;