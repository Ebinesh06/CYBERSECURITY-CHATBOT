import { Component, OnInit } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { CommonModule } from '@angular/common';
import { Router } from '@angular/router';
import { HttpClient } from '@angular/common/http';
@Component({
  selector: 'app-chat',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './chat.html',
  styleUrls: ['./chat.css']
})
export class ChatComponent implements OnInit {
  username: string = '';
  messages: any[] = [];
  userInput: string = '';
  isTyping: boolean = false;
  menuOpen = false;
  menuHistoryOpen = false;
  history: string[] = [];

constructor(private router: Router, private http: HttpClient) {}
  ngOnInit() {
    this.username = localStorage.getItem('username')?.trim() || '';
    this.history = this.loadHistory();
    if (!this.username) {
      this.router.navigate(['/']);
    }
  }

sendMessage() {
    const userMsg = this.userInput.trim();
    if (!userMsg) return;

    this.addToHistory(userMsg);
    this.messages.push({ sender: 'user', text: userMsg });
    this.userInput = '';
    this.isTyping = true;

    // Send the message to your FastAPI backend
    // Use 'http://127.0.0.1:8000/chat' if testing on the same laptop
    this.http.post<any>('http://127.0.0.1:8000/chat', { text: userMsg })
      .subscribe({
        next: (response) => {
          this.isTyping = false;
          this.messages.push({
            sender: 'bot',
            text: response.reply // Matches the "reply" key in your Python code
          });
        },
        error: (error) => {
          this.isTyping = false;
          this.messages.push({
            sender: 'bot',
            text: 'Error: Could not connect to the backend server.'
          });
          console.error('Connection error:', error);
        }
      });
  }

  quickAsk(question: string) {
    this.userInput = question;
    this.sendMessage();
  }

  toggleMenu() {
    this.menuOpen = !this.menuOpen;
    if (!this.menuOpen) {
      this.menuHistoryOpen = false;
    }
  }

  toggleHistory() {
    this.menuHistoryOpen = !this.menuHistoryOpen;
    if (this.menuHistoryOpen) {
      this.menuOpen = true;
    }
  }

  clearChat() {
    this.messages = [];
    this.userInput = '';
    this.isTyping = false;
  }

  addToHistory(query: string) {
    if (!query) return;
    const trimmed = query.trim();
    if (!trimmed) return;

    if (!this.history.includes(trimmed)) {
      this.history.unshift(trimmed);
      if (this.history.length > 20) {
        this.history.length = 20;
      }
      localStorage.setItem('searchHistory', JSON.stringify(this.history));
    }
  }

  loadHistory(): string[] {
    try {
      const saved = localStorage.getItem('searchHistory');
      return saved ? JSON.parse(saved) : [];
    } catch {
      return [];
    }
  }

  clearHistory() {
    this.history = [];
    localStorage.setItem('searchHistory', JSON.stringify(this.history));
    this.menuHistoryOpen = false;
  }

  signOut() {
    localStorage.removeItem('username');
    this.clearChat();
    this.menuOpen = false;
    this.router.navigate(['/']);
  }

  // getBotResponse(input: string): string {
  //   input = input.toLowerCase();

  //   if (input.includes('phishing')) {
  //     return 'Phishing is a cyber attack where attackers trick users into revealing sensitive information via fake emails or websites.';
  //   }

  //   if (input.includes('password')) {
  //     return 'Use strong passwords with a mix of letters, numbers, and symbols. Avoid reusing passwords.';
  //   }

  //   if (input.includes('malware')) {
  //     return 'Malware is malicious software designed to harm or exploit systems.';
  //   }

  //   if (input.includes('ransomware')) {
  //     return 'Ransomware locks your data and demands payment to restore access.';
  //   }

  //   if (input.includes('scam')) {
  //     return 'Scams trick users into giving money or personal data. Always verify sources before trusting.';
  //   }

  //   return 'I can help with cybersecurity topics like phishing, malware, and password safety.';
  // }
}