// mql5shim.hpp - emulazione minima del runtime MQL5 per compilare (g++) ed eseguire un EA MQL5 come C++.
// Due usi: 1) controllo sintattico/di tipo (g++ -fsyntax-only); 2) esecuzione su dati storici con un broker
// simulato (barre M1, bid/ask, stop lato server, storico delle operazioni, variabili globali, file).
#pragma once
#include <string>
#include <vector>
#include <map>
#include <set>
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <cstdint>
#include <cfloat>
#include <climits>
#include <algorithm>
#include <type_traits>
#include <stdexcept>
#include <utility>

typedef long long datetime;
typedef unsigned int color;
typedef unsigned long ulong;
typedef unsigned int uint;
typedef unsigned short ushort;
typedef unsigned char uchar;

[[noreturn]] void mql_fatal(const char* what, long long a = 0, long long b = 0);

//==================================================================== string
struct string : std::string
{
   string() {}
   string(const char* s) : std::string(s ? s : "") {}
   string(const char* s, size_t n) : std::string(s, n) {}
   string(const std::string& s) : std::string(s) {}
   string(std::string&& s) : std::string(std::move(s)) {}
   const std::string& str() const { return *this; }
};
inline string operator+(const string& a, const string& b) { return string(a.str() + b.str()); }
inline string operator+(const string& a, const char* b) { return string(a.str() + (b ? b : "")); }
inline string operator+(const char* a, const string& b) { return string(std::string(a ? a : "") + b.str()); }
inline bool operator==(const string& a, const string& b) { return a.str() == b.str(); }
inline bool operator!=(const string& a, const string& b) { return a.str() != b.str(); }
inline bool operator==(const string& a, const char* b) { return a.str() == (b ? b : ""); }
inline bool operator!=(const string& a, const char* b) { return !(a == b); }
inline bool operator<(const string& a, const string& b) { return a.str() < b.str(); }

//==================================================================== array dinamici
template<class T> struct MqlArr
{
   std::vector<T> v;
   bool series = false;
   MqlArr() {}
   template<size_t N> MqlArr(const T (&a)[N]) : v(a, a + N) {}
   int size() const { return (int)v.size(); }
   size_t idx(long long i) const
   {
      if(i < 0 || i >= (long long)v.size()) mql_fatal("array out of range", i, (long long)v.size());
      return series ? v.size() - 1 - (size_t)i : (size_t)i;
   }
   T& operator[](long long i) { return v[idx(i)]; }
   const T& operator[](long long i) const { return v[idx(i)]; }
};
template<class T> int ArraySize(const MqlArr<T>& a) { return a.size(); }
template<class T, size_t N> int ArraySize(const T (&)[N]) { return (int)N; }
template<class T> int ArrayResize(MqlArr<T>& a, int n, int reserve = 0)
{
   if(n < 0) return -1;
   if(reserve > 0 && a.v.capacity() < (size_t)(n + reserve)) a.v.reserve(n + reserve);
   a.v.resize(n);
   return n;
}
template<class T> bool ArraySetAsSeries(MqlArr<T>& a, bool s) { a.series = s; return true; }
template<class T> void ZeroMemory(T& x) { x = T(); }

//==================================================================== enumerazioni e costanti
enum ENUM_TIMEFRAMES { PERIOD_CURRENT = 0, PERIOD_M1 = 1, PERIOD_M5 = 5, PERIOD_M15 = 15, PERIOD_M30 = 30, PERIOD_H1 = 16385, PERIOD_H4 = 16388, PERIOD_D1 = 16408 };
enum ENUM_MA_METHOD { MODE_SMA, MODE_EMA, MODE_SMMA, MODE_LWMA };
enum ENUM_APPLIED_PRICE { PRICE_CLOSE = 1, PRICE_OPEN, PRICE_HIGH, PRICE_LOW, PRICE_MEDIAN, PRICE_TYPICAL, PRICE_WEIGHTED };
enum ENUM_SYMBOL_INFO_DOUBLE { SYMBOL_BID, SYMBOL_ASK, SYMBOL_POINT, SYMBOL_TRADE_TICK_VALUE, SYMBOL_TRADE_TICK_VALUE_PROFIT, SYMBOL_TRADE_TICK_VALUE_LOSS,
                               SYMBOL_TRADE_TICK_SIZE, SYMBOL_TRADE_CONTRACT_SIZE, SYMBOL_VOLUME_MIN, SYMBOL_VOLUME_MAX, SYMBOL_VOLUME_STEP };
enum ENUM_SYMBOL_INFO_INTEGER { SYMBOL_DIGITS = 100, SYMBOL_SPREAD, SYMBOL_TRADE_STOPS_LEVEL, SYMBOL_TRADE_FREEZE_LEVEL, SYMBOL_TRADE_MODE, SYMBOL_FILLING_MODE };
enum ENUM_SYMBOL_TRADE_MODE { SYMBOL_TRADE_MODE_DISABLED, SYMBOL_TRADE_MODE_LONGONLY, SYMBOL_TRADE_MODE_SHORTONLY, SYMBOL_TRADE_MODE_CLOSEONLY, SYMBOL_TRADE_MODE_FULL };
enum ENUM_POSITION_PROPERTY_INTEGER { POSITION_TICKET = 200, POSITION_TIME, POSITION_TIME_MSC, POSITION_TIME_UPDATE, POSITION_TYPE, POSITION_MAGIC, POSITION_IDENTIFIER, POSITION_REASON };
enum ENUM_POSITION_PROPERTY_DOUBLE { POSITION_VOLUME = 300, POSITION_PRICE_OPEN, POSITION_SL, POSITION_TP, POSITION_PRICE_CURRENT, POSITION_SWAP, POSITION_PROFIT };
enum ENUM_POSITION_PROPERTY_STRING { POSITION_SYMBOL = 400, POSITION_COMMENT };
enum ENUM_POSITION_TYPE { POSITION_TYPE_BUY, POSITION_TYPE_SELL };
enum ENUM_DEAL_PROPERTY_INTEGER { DEAL_TICKET = 500, DEAL_ORDER, DEAL_TIME, DEAL_TIME_MSC, DEAL_TYPE, DEAL_ENTRY, DEAL_MAGIC, DEAL_REASON, DEAL_POSITION_ID };
enum ENUM_DEAL_PROPERTY_DOUBLE { DEAL_VOLUME = 600, DEAL_PRICE, DEAL_COMMISSION, DEAL_SWAP, DEAL_PROFIT, DEAL_FEE };
enum ENUM_DEAL_PROPERTY_STRING { DEAL_SYMBOL = 700, DEAL_COMMENT };
enum ENUM_DEAL_ENTRY { DEAL_ENTRY_IN, DEAL_ENTRY_OUT, DEAL_ENTRY_INOUT, DEAL_ENTRY_OUT_BY };
enum ENUM_DEAL_TYPE { DEAL_TYPE_BUY, DEAL_TYPE_SELL, DEAL_TYPE_BALANCE, DEAL_TYPE_CREDIT };
enum ENUM_DEAL_REASON { DEAL_REASON_CLIENT, DEAL_REASON_MOBILE, DEAL_REASON_WEB, DEAL_REASON_EXPERT, DEAL_REASON_SL, DEAL_REASON_TP, DEAL_REASON_SO };
enum ENUM_ACCOUNT_INFO_DOUBLE { ACCOUNT_BALANCE = 800, ACCOUNT_CREDIT, ACCOUNT_PROFIT, ACCOUNT_EQUITY, ACCOUNT_MARGIN, ACCOUNT_MARGIN_FREE };
enum ENUM_ACCOUNT_INFO_INTEGER { ACCOUNT_LOGIN = 900, ACCOUNT_TRADE_MODE, ACCOUNT_LEVERAGE, ACCOUNT_MARGIN_MODE };
enum ENUM_ACCOUNT_MARGIN_MODE { ACCOUNT_MARGIN_MODE_RETAIL_NETTING, ACCOUNT_MARGIN_MODE_EXCHANGE, ACCOUNT_MARGIN_MODE_RETAIL_HEDGING };
enum ENUM_ORDER_TYPE { ORDER_TYPE_BUY, ORDER_TYPE_SELL };
enum ENUM_MQL_INFO_INTEGER { MQL_TESTER = 1000, MQL_VISUAL_MODE, MQL_OPTIMIZATION };
enum ENUM_OBJECT { OBJ_LABEL = 1100, OBJ_BUTTON, OBJ_EDIT, OBJ_RECTANGLE_LABEL };
enum ENUM_OBJECT_PROPERTY_INTEGER { OBJPROP_COLOR = 1200, OBJPROP_CORNER, OBJPROP_XDISTANCE, OBJPROP_YDISTANCE, OBJPROP_XSIZE, OBJPROP_YSIZE, OBJPROP_FONTSIZE,
                                    OBJPROP_BGCOLOR, OBJPROP_STATE, OBJPROP_BORDER_TYPE, OBJPROP_BACK, OBJPROP_SELECTABLE, OBJPROP_HIDDEN };
enum ENUM_OBJECT_PROPERTY_STRING { OBJPROP_TEXT = 1300, OBJPROP_FONT, OBJPROP_TOOLTIP };
enum ENUM_BASE_CORNER { CORNER_LEFT_UPPER, CORNER_LEFT_LOWER, CORNER_RIGHT_LOWER, CORNER_RIGHT_UPPER };
enum ENUM_BORDER_TYPE { BORDER_FLAT, BORDER_RAISED, BORDER_SUNKEN };
enum ENUM_CHART_EVENT { CHARTEVENT_KEYDOWN, CHARTEVENT_MOUSE_MOVE, CHARTEVENT_OBJECT_CREATE, CHARTEVENT_OBJECT_CHANGE, CHARTEVENT_OBJECT_DELETE,
                        CHARTEVENT_CLICK, CHARTEVENT_OBJECT_CLICK, CHARTEVENT_OBJECT_DRAG, CHARTEVENT_OBJECT_ENDEDIT };
enum ENUM_INIT_RETCODE { INIT_SUCCEEDED = 0, INIT_FAILED = 1, INIT_PARAMETERS_INCORRECT = 32767, INIT_AGENT_NOT_SUITABLE };
enum ENUM_CALENDAR_EVENT_IMPORTANCE { CALENDAR_IMPORTANCE_NONE, CALENDAR_IMPORTANCE_LOW, CALENDAR_IMPORTANCE_MODERATE, CALENDAR_IMPORTANCE_HIGH };

#define INVALID_HANDLE (-1)
#define WHOLE_ARRAY (-1)
#define CP_ACP 0
#define CP_UTF8 65001
#define TIME_DATE 1
#define TIME_MINUTES 2
#define TIME_SECONDS 4
#define FILE_READ 1
#define FILE_WRITE 2
#define FILE_BIN 4
#define FILE_CSV 8
#define FILE_TXT 16
#define FILE_ANSI 32
#define FILE_UNICODE 64
#define FILE_SHARE_READ 128
#define FILE_SHARE_WRITE 256
#define FILE_REWRITE 512
#define FILE_COMMON 4096
#define MB_OK 0
#define MB_YESNO 4
#define IDYES 6
#define IDNO 7
#define TRADE_RETCODE_REQUOTE 10004
#define TRADE_RETCODE_REJECT 10006
#define TRADE_RETCODE_PLACED 10008
#define TRADE_RETCODE_DONE 10009
#define TRADE_RETCODE_DONE_PARTIAL 10010
#define TRADE_RETCODE_INVALID 10013
#define TRADE_RETCODE_INVALID_VOLUME 10014
#define TRADE_RETCODE_INVALID_STOPS 10016
#define TRADE_RETCODE_MARKET_CLOSED 10018
#define TRADE_RETCODE_NO_MONEY 10019
#define TRADE_RETCODE_PRICE_CHANGED 10020
#define TRADE_RETCODE_PRICE_OFF 10021
#define TRADE_RETCODE_POSITION_CLOSED 10036

const color clrWhite = 0xFFFFFF, clrBlack = 0x000000, clrGold = 0x00D7FF, clrLime = 0x00FF00, clrTomato = 0x4763FF, clrSilver = 0xC0C0C0,
            clrSeaGreen = 0x578B2E, clrSteelBlue = 0xB48246, clrDarkOrange = 0x008CFF, clrSlateGray = 0x908070, clrFireBrick = 0x2222B2,
            clrGoldenrod = 0x20A5DA, clrRed = 0x0000FF, clrDimGray = 0x696969, clrGray = 0x808080, clrYellow = 0x00FFFF;

struct MqlRates { datetime time; double open, high, low, close; long tick_volume; int spread; long real_volume; };
struct MqlDateTime { int year, mon, day, hour, min, sec, day_of_week, day_of_year; };
struct MqlCalendarValue { ulong id; ulong event_id; datetime time; datetime period; int revision; long actual_value, prev_value, revised_prev_value, forecast_value; int impact_type; };
struct MqlCalendarEvent { ulong id; int type; int sector; int frequency; int time_mode; ulong country_id; int unit; ENUM_CALENDAR_EVENT_IMPORTANCE importance; int multiplier; uint digits; string source_url; string event_code; string name; };
struct MqlTradeResult { uint retcode; ulong deal; ulong order; double volume; double price; double bid; double ask; string comment; };

//==================================================================== date
inline long long sim_days_from_civil(long long y, unsigned m, unsigned d)
{
   y -= m <= 2;
   const long long era = (y >= 0 ? y : y - 399) / 400;
   const unsigned yoe = (unsigned)(y - era * 400);
   const unsigned doy = (153 * (m + (m > 2 ? -3 : 9)) + 2) / 5 + d - 1;
   const unsigned doe = yoe * 365 + yoe / 4 - yoe / 100 + doy;
   return era * 146097 + (long long)doe - 719468;
}
inline void sim_civil_from_days(long long z, int& y, int& m, int& d)
{
   z += 719468;
   const long long era = (z >= 0 ? z : z - 146096) / 146097;
   const unsigned doe = (unsigned)(z - era * 146097);
   const unsigned yoe = (doe - doe / 1460 + doe / 36524 - doe / 146096) / 365;
   const long long yy = (long long)yoe + era * 400;
   const unsigned doy = doe - (365 * yoe + yoe / 4 - yoe / 100);
   const unsigned mp = (5 * doy + 2) / 153;
   d = (int)(doy - (153 * mp + 2) / 5 + 1);
   m = (int)(mp < 10 ? mp + 3 : mp - 9);
   y = (int)(yy + (m <= 2));
}
inline bool TimeToStruct(datetime t, MqlDateTime& s)
{
   long long days = t >= 0 ? t / 86400 : -((-t + 86399) / 86400);
   long long sec = t - days * 86400;
   sim_civil_from_days(days, s.year, s.mon, s.day);
   s.hour = (int)(sec / 3600); s.min = (int)(sec % 3600 / 60); s.sec = (int)(sec % 60);
   s.day_of_week = (int)(((days % 7) + 11) % 7);   // 1970-01-01 = giovedi' (4)
   s.day_of_year = (int)(days - sim_days_from_civil(s.year, 1, 1));
   return true;
}
inline datetime StructToTime(const MqlDateTime& s)
{
   return sim_days_from_civil(s.year, (unsigned)s.mon, (unsigned)s.day) * 86400 + s.hour * 3600 + s.min * 60 + s.sec;
}

//==================================================================== matematica
template<class A, class B> inline auto MathMax(A a, B b) -> typename std::common_type<A, B>::type { typedef typename std::common_type<A, B>::type T; return (T)a > (T)b ? (T)a : (T)b; }
template<class A, class B> inline auto MathMin(A a, B b) -> typename std::common_type<A, B>::type { typedef typename std::common_type<A, B>::type T; return (T)a < (T)b ? (T)a : (T)b; }
inline double MathAbs(double x) { return std::fabs(x); }
inline double MathFloor(double x) { return std::floor(x); }
inline double MathCeil(double x) { return std::ceil(x); }
inline double MathRound(double x) { return std::round(x); }
inline double MathPow(double a, double b) { return std::pow(a, b); }
inline double MathLog10(double a) { return std::log10(a); }
inline double MathSqrt(double a) { return std::sqrt(a); }
inline double NormalizeDouble(double v, int d) { double p = std::pow(10.0, d); return std::round(v * p) / p; }

//==================================================================== stringhe
inline int StringLen(const string& s) { return (int)s.size(); }
inline int StringFind(const string& s, const string& sub, int start = 0)
{
   if(start < 0) start = 0;
   if((size_t)start > s.size()) return -1;
   size_t p = s.find(sub, (size_t)start);
   return p == std::string::npos ? -1 : (int)p;
}
inline string StringSubstr(const string& s, int start, int len = -1)
{
   if(start < 0) start = 0;
   if((size_t)start >= s.size()) return string();
   return string(s.substr((size_t)start, len < 0 ? std::string::npos : (size_t)len));
}
inline int StringSplit(const string& s, ushort sep, MqlArr<string>& out)
{
   out.v.clear();
   if(s.empty()) return 0;
   size_t a = 0;
   while(true)
   {
      size_t b = s.find((char)sep, a);
      out.v.push_back(string(s.substr(a, b == std::string::npos ? std::string::npos : b - a)));
      if(b == std::string::npos) break;
      a = b + 1;
   }
   return out.size();
}
inline int StringTrimLeft(string& s) { size_t n = 0; while(n < s.size() && (s[n] == ' ' || s[n] == '\t' || s[n] == '\r' || s[n] == '\n')) n++; s.erase(0, n); return (int)n; }
inline int StringTrimRight(string& s) { size_t n = 0; while(!s.empty() && (s.back() == ' ' || s.back() == '\t' || s.back() == '\r' || s.back() == '\n')) { s.pop_back(); n++; } return (int)n; }
inline bool StringToUpper(string& s) { for(auto& c : s) c = (char)toupper((unsigned char)c); return true; }
inline int StringReplace(string& s, const string& f, const string& r)
{
   if(f.empty()) return 0;
   int n = 0; size_t p = 0;
   while((p = s.find(f, p)) != std::string::npos) { s.replace(p, f.size(), r); p += r.size(); n++; }
   return n;
}
inline long StringToInteger(const string& s) { return std::strtol(s.c_str(), nullptr, 10); }
inline double StringToDouble(const string& s) { return std::strtod(s.c_str(), nullptr); }
inline string IntegerToString(long long v, int len = 0, ushort fill = ' ')
{
   std::string r = std::to_string(v);
   while((int)r.size() < len) r.insert(r.begin(), (char)fill);
   return string(r);
}
inline string DoubleToString(double v, int digits = 8)
{
   char b[64]; std::snprintf(b, sizeof(b), "%.*f", digits < 0 ? 8 : digits, v); return string(b);
}
inline string CharArrayToString(const MqlArr<char>& a, int start = 0, int count = -1, uint codepage = 0)
{
   (void)codepage;
   if(start < 0 || start >= a.size()) return string();
   int n = count < 0 ? a.size() - start : std::min(count, a.size() - start);
   std::string r(a.v.data() + start, (size_t)n);
   size_t z = r.find('\0'); if(z != std::string::npos) r.resize(z);
   return string(r);
}
inline string TimeToString(datetime t, int flags = TIME_DATE | TIME_MINUTES)
{
   MqlDateTime s; TimeToStruct(t, s); char b[64]; std::string r;
   if(flags & TIME_DATE) { std::snprintf(b, sizeof(b), "%04d.%02d.%02d", s.year, s.mon, s.day); r += b; }
   if(flags & (TIME_MINUTES | TIME_SECONDS))
   {
      if(!r.empty()) r += " ";
      if(flags & TIME_SECONDS) std::snprintf(b, sizeof(b), "%02d:%02d:%02d", s.hour, s.min, s.sec);
      else std::snprintf(b, sizeof(b), "%02d:%02d", s.hour, s.min);
      r += b;
   }
   return string(r);
}
inline datetime StringToTime(const string& s)
{
   int y = 0, mo = 0, d = 0, h = 0, mi = 0, se = 0;
   int n = std::sscanf(s.c_str(), "%d.%d.%d %d:%d:%d", &y, &mo, &d, &h, &mi, &se);
   if(n < 3) return 0;
   MqlDateTime t; t.year = y; t.mon = mo; t.day = d; t.hour = h; t.min = mi; t.sec = se;
   return StructToTime(t);
}

// argomenti di StringFormat/PrintFormat
struct FmtArg { int k; long long i; unsigned long long u; double d; std::string s; };   // k: 0 int, 1 uint, 2 double, 3 string
template<class T> FmtArg mkfmt(const T& v)
{
   FmtArg a{};
   if constexpr(std::is_same<T, string>::value || std::is_same<T, std::string>::value) { a.k = 3; a.s = v; }
   else if constexpr(std::is_same<typename std::decay<T>::type, const char*>::value || std::is_same<typename std::decay<T>::type, char*>::value) { a.k = 3; a.s = v ? v : ""; }
   else if constexpr(std::is_floating_point<T>::value) { a.k = 2; a.d = (double)v; }
   else if constexpr(std::is_enum<T>::value) { a.k = 0; a.i = (long long)v; }
   else if constexpr(std::is_unsigned<T>::value) { a.k = 1; a.u = (unsigned long long)v; a.i = (long long)v; }
   else { static_assert(std::is_integral<T>::value, "tipo non supportato in StringFormat"); a.k = 0; a.i = (long long)v; }
   return a;
}
inline string sim_format(const std::string& f, const std::vector<FmtArg>& args)
{
   std::string out; size_t ai = 0;
   for(size_t i = 0; i < f.size(); i++)
   {
      if(f[i] != '%') { out += f[i]; continue; }
      if(i + 1 < f.size() && f[i + 1] == '%') { out += '%'; i++; continue; }
      std::string spec = "%"; size_t j = i + 1;
      while(j < f.size() && strchr("-+ 0#", f[j])) spec += f[j++];
      while(j < f.size() && isdigit((unsigned char)f[j])) spec += f[j++];
      if(j < f.size() && f[j] == '.') { spec += f[j++]; while(j < f.size() && isdigit((unsigned char)f[j])) spec += f[j++]; }
      // modificatori di lunghezza (ignorati: si usa sempre 64 bit)
      while(j < f.size() && strchr("hlLqjzt", f[j])) j++;
      if(j + 2 < f.size() && f[j] == 'I' && f[j + 1] == '6' && f[j + 2] == '4') j += 3;
      else if(j + 2 < f.size() && f[j] == 'I' && f[j + 1] == '3' && f[j + 2] == '2') j += 3;
      if(j >= f.size()) mql_fatal("StringFormat: specifica incompleta");
      char conv = f[j]; i = j;
      if(ai >= args.size()) mql_fatal("StringFormat: argomenti insufficienti", (long long)ai);
      const FmtArg& a = args[ai++];
      char b[512];
      if(strchr("di", conv)) { if(a.k == 2 || a.k == 3) mql_fatal("StringFormat: %d con tipo non intero"); spec += "lld"; std::snprintf(b, sizeof(b), spec.c_str(), a.i); }
      else if(strchr("uxXo", conv)) { if(a.k == 2 || a.k == 3) mql_fatal("StringFormat: %u con tipo non intero"); spec += "ll"; spec += conv; std::snprintf(b, sizeof(b), spec.c_str(), a.k == 1 ? a.u : (unsigned long long)a.i); }
      else if(strchr("fFeEgG", conv)) { if(a.k == 3) mql_fatal("StringFormat: %f con stringa"); spec += conv; std::snprintf(b, sizeof(b), spec.c_str(), a.k == 2 ? a.d : (double)a.i); }
      else if(conv == 's') { if(a.k != 3) mql_fatal("StringFormat: %s con tipo non stringa"); spec += 's'; std::snprintf(b, sizeof(b), spec.c_str(), a.s.c_str()); }
      else if(conv == 'c') { spec += 'c'; std::snprintf(b, sizeof(b), spec.c_str(), (int)a.i); }
      else mql_fatal("StringFormat: conversione sconosciuta", conv);
      out += b;
   }
   if(ai != args.size()) mql_fatal("StringFormat: troppi argomenti", (long long)ai, (long long)args.size());
   return string(out);
}
template<class... A> string StringFormat(const string& f, const A&... a) { return sim_format(f, std::vector<FmtArg>{mkfmt(a)...}); }

template<class T> std::string sim_tostr(const T& v)
{
   if constexpr(std::is_same<T, string>::value || std::is_same<T, std::string>::value) return v;
   else if constexpr(std::is_same<typename std::decay<T>::type, const char*>::value) return v ? v : "";
   else if constexpr(std::is_same<T, bool>::value) return v ? "true" : "false";
   else if constexpr(std::is_floating_point<T>::value) { char b[64]; std::snprintf(b, sizeof(b), "%.8g", (double)v); return b; }
   else return std::to_string((long long)v);
}

//==================================================================== simulatore
namespace sim
{
struct Series
{
   std::vector<MqlRates> bars;     // candele complete del timeframe
   std::vector<datetime> first;    // orario del primo M1 di ogni candela
   std::vector<size_t>   m1first;  // indice del primo M1
   size_t cur = 0;                 // candela in formazione (ultima con first <= now)
   bool started = false;
};
struct Symbol
{
   std::string name;
   bool tradeable = true;
   int digits = 2;
   double point = 0.01, tick_size = 0.01, tick_value = 0.01, contract = 1.0;
   double vstep = 0.01, vmin = 0.01, vmax = 100.0;
   long stops = 0;
   double spread_rel = 0.0, spread_min = 0.0;
   std::vector<MqlRates> m1;
   long long cur = -1;             // ultimo M1 con time <= now
   bool tick = false;              // c'e' un M1 che apre esattamente adesso
   std::map<int, Series> tf;       // minuti -> serie
   double bid() const
   {
      if(cur < 0) return 0.0;
      return tick ? m1[(size_t)cur].open : m1[(size_t)cur].close;
   }
   double spread_at(double p) const { return std::max(spread_min, spread_rel * p); }
   double ask() const { double b = bid(); return b > 0 ? b + spread_at(b) : 0.0; }
};
struct Position { ulong ticket; std::string sym; long magic; int type; double vol, open, sl, tp, sl0; datetime time; std::string comment; };
struct Deal { ulong ticket; ulong order; datetime time; long magic; int entry; int type; int reason; double volume, price, profit, swap, commission; std::string sym; ulong pos; std::string comment; };
struct Indicator { int sym; int tfmin; int period; std::vector<double> ema; };
struct FileH { std::FILE* f = nullptr; int flags = 0; char delim = ';'; std::string path; };
struct Closed { ulong ticket; std::string sym; long magic; int type; double vol, open, close, sl0, profit, risk_money; datetime t_open, t_close; std::string comment; int reason; };

struct State
{
   datetime now = 0;
   bool tester = true, visual = false, quiet = true;
   long login = 12345678;
   long leverage = 30;
   double balance = 0;
   std::vector<Symbol> syms;
   std::vector<Position> pos;
   std::vector<Deal> deals;
   std::vector<Closed> closed;
   size_t hsel_a = 0, hsel_b = 0;   // storico selezionato [a, b)
   long long psel = -1;             // posizione selezionata
   ulong next_ticket = 1000;
   std::map<std::string, double> gv;
   std::vector<Indicator> ind;
   std::map<int, FileH> files;
   int next_file = 1;
   std::string files_dir = "files", common_dir = "common";
   int last_error = 0;
   std::map<std::string, std::map<int, long long>> obj_i;
   std::map<std::string, std::map<int, std::string>> obj_s;
   std::vector<std::string> prints;
   bool keep_prints = false;
   long chart_id = 132456789012345678L;
   long long gmt_off = 0;                // solo dal vivo: server - UTC
   std::string web_json;                 // risposta di prova per WebRequest
   std::vector<MqlCalendarValue> cal_vals; std::vector<MqlCalendarEvent> cal_evs; std::vector<std::string> cal_cur;
};
inline State& S() { static State s; return s; }

inline int sym_index(const std::string& n) { auto& s = S(); for(size_t i = 0; i < s.syms.size(); i++) if(s.syms[i].name == n) return (int)i; return -1; }
inline Symbol* sym(const std::string& n) { int i = sym_index(n); return i < 0 ? nullptr : &S().syms[(size_t)i]; }
inline int tf_minutes(ENUM_TIMEFRAMES tf)
{
   switch(tf)
   {
      case PERIOD_M1: return 1; case PERIOD_M5: return 5; case PERIOD_M15: return 15; case PERIOD_M30: return 30;
      case PERIOD_H1: return 60; case PERIOD_H4: return 240; case PERIOD_D1: return 1440; default: return 0;
   }
}
inline void build_series(Symbol& s, int mins)
{
   Series& se = s.tf[mins];
   se.bars.clear(); se.first.clear(); se.m1first.clear();
   long long len = mins * 60LL;
   for(size_t i = 0; i < s.m1.size(); i++)
   {
      const MqlRates& r = s.m1[i];
      datetime st = r.time - ((r.time % len) + len) % len;
      if(se.bars.empty() || se.bars.back().time != st)
      {
         MqlRates b = r; b.time = st; se.bars.push_back(b); se.first.push_back(r.time); se.m1first.push_back(i);
      }
      else
      {
         MqlRates& b = se.bars.back();
         b.high = std::max(b.high, r.high); b.low = std::min(b.low, r.low); b.close = r.close; b.tick_volume += r.tick_volume;
      }
   }
   se.cur = 0; se.started = false;
}
// candela in formazione: solo i dati noti fino ad adesso
inline MqlRates forming(const Symbol& s, const Series& se, size_t k)
{
   MqlRates b = s.m1[se.m1first[k]];
   b.time = se.bars[k].time;
   b.high = b.open; b.low = b.open; b.close = b.open; b.tick_volume = 0;
   for(size_t i = se.m1first[k]; i <= (size_t)s.cur && i < s.m1.size(); i++)
   {
      const MqlRates& r = s.m1[i];
      if(r.time >= se.bars[k].time + (datetime)0 && (k + 1 >= se.bars.size() || r.time < se.bars[k + 1].time))
      {
         if(r.time < S().now) { b.high = std::max(b.high, r.high); b.low = std::min(b.low, r.low); b.close = r.close; b.tick_volume += r.tick_volume; }
         else { b.high = std::max(b.high, r.open); b.low = std::min(b.low, r.open); b.close = r.open; b.tick_volume += 1; }
      }
   }
   return b;
}
inline Series* series(Symbol& s, ENUM_TIMEFRAMES tf)
{
   int m = tf_minutes(tf);
   if(m <= 1) return nullptr;
   auto it = s.tf.find(m);
   if(it == s.tf.end()) { build_series(s, m); it = s.tf.find(m); }
   Series& se = it->second;
   // avanza la candela corrente (il tempo cresce sempre)
   if(se.bars.empty() || se.first[0] > S().now) { se.started = false; return &se; }
   if(!se.started) { se.cur = (size_t)(std::upper_bound(se.first.begin(), se.first.end(), S().now) - se.first.begin()) - 1; se.started = true; }
   while(se.cur + 1 < se.first.size() && se.first[se.cur + 1] <= S().now) se.cur++;
   return &se;
}
inline double value_per_price(const Symbol& s) { return s.tick_value / s.tick_size; }   // valuta del conto per 1.0 di prezzo e 1 lotto
inline double pos_profit(const Symbol& s, const Position& p)
{
   double px = p.type == 0 ? s.bid() : s.ask();
   return (p.type == 0 ? px - p.open : p.open - px) * p.vol * value_per_price(s);
}
inline double margin_of(const Symbol& s, double vol, double price) { return vol * s.contract * price / (double)S().leverage; }
inline double equity()
{
   auto& st = S(); double e = st.balance;
   for(auto& p : st.pos) { Symbol* s = sym(p.sym); if(s) e += pos_profit(*s, p); }
   return e;
}
inline double margin_used()
{
   auto& st = S(); double m = 0;
   for(auto& p : st.pos) { Symbol* s = sym(p.sym); if(s) m += margin_of(*s, p.vol, p.open); }
   return m;
}
inline void add_deal(const Position& p, int entry, int reason, double price, double profit)
{
   auto& st = S();
   Deal d; d.ticket = st.next_ticket++; d.order = p.ticket; d.time = st.now; d.magic = p.magic; d.entry = entry;
   d.type = (entry == DEAL_ENTRY_IN) == (p.type == 0) ? DEAL_TYPE_BUY : DEAL_TYPE_SELL; d.reason = reason;
   d.volume = p.vol; d.price = price; d.profit = profit; d.swap = 0; d.commission = 0; d.sym = p.sym; d.pos = p.ticket; d.comment = p.comment;
   st.deals.push_back(d);
}
inline void close_at(size_t i, double price, int reason)
{
   auto& st = S(); Position p = st.pos[i]; Symbol* s = sym(p.sym);
   double profit = (p.type == 0 ? price - p.open : p.open - price) * p.vol * value_per_price(*s);
   profit = std::round(profit * 100.0) / 100.0;
   st.balance += profit;
   add_deal(p, DEAL_ENTRY_OUT, reason, price, profit);
   Closed c; c.ticket = p.ticket; c.sym = p.sym; c.magic = p.magic; c.type = p.type; c.vol = p.vol; c.open = p.open; c.close = price; c.sl0 = p.sl0;
   c.profit = profit; c.risk_money = std::fabs(p.open - p.sl0) * p.vol * value_per_price(*s); c.t_open = p.time; c.t_close = st.now; c.comment = p.comment; c.reason = reason;
   st.closed.push_back(c);
   st.pos.erase(st.pos.begin() + (long)i);
   st.psel = -1;
}
// stop lato server sull'apertura (gap) e poi sul range del minuto
inline void process_sl(bool at_open)
{
   auto& st = S();
   for(size_t i = st.pos.size(); i-- > 0;)
   {
      Position& p = st.pos[i];
      Symbol* s = sym(p.sym);
      if(!s || !s->tick || p.sl <= 0) continue;
      const MqlRates& r = s->m1[(size_t)s->cur];
      if(p.type == 0)
      {
         if(at_open) { if(r.open <= p.sl) close_at(i, r.open, DEAL_REASON_SL); }
         else if(r.low <= p.sl) close_at(i, p.sl, DEAL_REASON_SL);
      }
      else
      {
         double so = s->spread_at(r.open);
         if(at_open) { if(r.open + so >= p.sl) close_at(i, r.open + so, DEAL_REASON_SL); }
         else if(r.high + s->spread_at(r.high) >= p.sl) close_at(i, p.sl, DEAL_REASON_SL);
      }
   }
}
inline void advance(datetime t)
{
   auto& st = S(); st.now = t;
   for(auto& s : st.syms)
   {
      while(s.cur + 1 < (long long)s.m1.size() && s.m1[(size_t)(s.cur + 1)].time <= t) s.cur++;
      s.tick = s.cur >= 0 && s.m1[(size_t)s.cur].time == t;
   }
}
inline uint open_position(const std::string& name, int type, double vol, double sl, double tp, long magic, const std::string& comment, ulong& ticket, double& price)
{
   auto& st = S(); Symbol* s = sym(name);
   if(!s || !s->tradeable) return TRADE_RETCODE_INVALID;
   if(!s->tick) return TRADE_RETCODE_MARKET_CLOSED;
   if(vol < s->vmin - 1e-9 || vol > s->vmax + 1e-9 || std::fabs(vol / s->vstep - std::round(vol / s->vstep)) > 1e-6) return TRADE_RETCODE_INVALID_VOLUME;
   double bid = s->bid(), ask = s->ask(); price = type == 0 ? ask : bid;
   double minD = (double)s->stops * s->point;
   if(sl > 0 && ((type == 0 && sl > bid - minD) || (type == 1 && sl < ask + minD))) return TRADE_RETCODE_INVALID_STOPS;
   if(margin_used() + margin_of(*s, vol, price) > equity()) return TRADE_RETCODE_NO_MONEY;
   Position p; p.ticket = st.next_ticket++; p.sym = name; p.magic = magic; p.type = type; p.vol = vol; p.open = price; p.sl = sl; p.tp = tp; p.sl0 = sl;
   p.time = st.now; p.comment = comment;
   st.pos.push_back(p);
   add_deal(p, DEAL_ENTRY_IN, DEAL_REASON_EXPERT, price, 0.0);
   ticket = p.ticket;
   return TRADE_RETCODE_DONE;
}
inline long long find_pos(ulong ticket) { auto& st = S(); for(size_t i = 0; i < st.pos.size(); i++) if(st.pos[i].ticket == ticket) return (long long)i; return -1; }
inline uint close_position(ulong ticket, double& price)
{
   long long i = find_pos(ticket);
   if(i < 0) return TRADE_RETCODE_POSITION_CLOSED;
   Position& p = S().pos[(size_t)i]; Symbol* s = sym(p.sym);
   if(!s->tick) return TRADE_RETCODE_MARKET_CLOSED;
   price = p.type == 0 ? s->bid() : s->ask();
   close_at((size_t)i, price, DEAL_REASON_EXPERT);
   return TRADE_RETCODE_DONE;
}
inline uint modify_position(ulong ticket, double sl, double tp)
{
   long long i = find_pos(ticket);
   if(i < 0) return TRADE_RETCODE_POSITION_CLOSED;
   Position& p = S().pos[(size_t)i]; Symbol* s = sym(p.sym);
   if(!s->tick) return TRADE_RETCODE_MARKET_CLOSED;
   double minD = (double)s->stops * s->point;
   if(sl > 0 && ((p.type == 0 && sl > s->bid() - minD) || (p.type == 1 && sl < s->ask() + minD))) return TRADE_RETCODE_INVALID_STOPS;
   p.sl = sl; p.tp = tp;
   return TRADE_RETCODE_DONE;
}
inline void deposit(double amount)
{
   auto& st = S(); st.balance += amount;
   Deal d{}; d.ticket = st.next_ticket++; d.time = st.now; d.magic = 0; d.entry = DEAL_ENTRY_IN; d.type = DEAL_TYPE_BALANCE; d.profit = amount;
   st.deals.push_back(d);
}
inline void withdraw(double amount)
{
   auto& st = S(); st.balance -= amount;
   Deal d{}; d.ticket = st.next_ticket++; d.time = st.now; d.magic = 0; d.entry = DEAL_ENTRY_OUT; d.type = DEAL_TYPE_BALANCE; d.profit = -amount;
   st.deals.push_back(d);
}
// equity peggiore nel minuto corrente (massimo/minimo della candela M1 per le posizioni aperte)
inline double worst_equity()
{
   auto& st = S(); double e = st.balance;
   for(auto& p : st.pos)
   {
      Symbol* s = sym(p.sym); if(!s) continue;
      double px;
      if(s->tick) { const MqlRates& r = s->m1[(size_t)s->cur]; px = p.type == 0 ? r.low : r.high + s->spread_at(r.high); }
      else px = p.type == 0 ? s->bid() : s->ask();
      e += (p.type == 0 ? px - p.open : p.open - px) * p.vol * value_per_price(*s);
   }
   return e;
}
inline void print_line(const std::string& s) { auto& st = S(); if(st.keep_prints) st.prints.push_back(s); if(!st.quiet) std::fprintf(stderr, "%s\n", s.c_str()); }
} // namespace sim

[[noreturn]] inline void mql_fatal(const char* what, long long a, long long b)
{
   char buf[256]; std::snprintf(buf, sizeof(buf), "ERRORE CRITICO MQL5: %s (%lld, %lld) alle %s", what, a, b, TimeToString(sim::S().now, TIME_DATE | TIME_SECONDS).c_str());
   throw std::runtime_error(buf);
}

//==================================================================== API: tempo, info
inline datetime TimeCurrent() { return sim::S().now; }
inline datetime TimeTradeServer() { return sim::S().now; }
inline datetime TimeGMT() { auto& s = sim::S(); return s.tester ? s.now : s.now - s.gmt_off; }   // nel tester MT5 coincide con l'orario simulato
inline int MQLInfoInteger(ENUM_MQL_INFO_INTEGER p) { auto& s = sim::S(); return p == MQL_TESTER ? (int)s.tester : (p == MQL_VISUAL_MODE ? (int)s.visual : 0); }
inline uint GetTickCount() { return (uint)(sim::S().now * 1000); }
inline void ResetLastError() { sim::S().last_error = 0; }
inline int GetLastError() { return sim::S().last_error; }
template<class... A> void Print(const A&... a) { std::string s; ((s += sim_tostr(a)), ...); sim::print_line(s); }
template<class... A> void Alert(const A&... a) { std::string s = "ALERT: "; ((s += sim_tostr(a)), ...); sim::print_line(s); }
template<class... A> bool PrintFormat(const string& f, const A&... a) { sim::print_line(StringFormat(f, a...)); return true; }
inline int MessageBox(const string& text, const string& caption = string(), int flags = 0) { (void)text; (void)caption; (void)flags; return IDYES; }
inline bool EventSetTimer(int s) { (void)s; return true; }
inline void EventKillTimer() {}

//==================================================================== API: account
inline double AccountInfoDouble(ENUM_ACCOUNT_INFO_DOUBLE p)
{
   switch(p)
   {
      case ACCOUNT_BALANCE: return sim::S().balance;
      case ACCOUNT_EQUITY: return sim::equity();
      case ACCOUNT_PROFIT: return sim::equity() - sim::S().balance;
      case ACCOUNT_MARGIN: return sim::margin_used();
      case ACCOUNT_MARGIN_FREE: return sim::equity() - sim::margin_used();
      default: return 0.0;
   }
}
inline long AccountInfoInteger(ENUM_ACCOUNT_INFO_INTEGER p)
{
   switch(p)
   {
      case ACCOUNT_LOGIN: return sim::S().login;
      case ACCOUNT_LEVERAGE: return sim::S().leverage;
      case ACCOUNT_MARGIN_MODE: return ACCOUNT_MARGIN_MODE_RETAIL_HEDGING;
      default: return 0;
   }
}

//==================================================================== API: simboli e serie
inline int SymbolsTotal(bool selected) { (void)selected; return (int)sim::S().syms.size(); }
inline string SymbolName(int i, bool selected) { (void)selected; auto& s = sim::S(); return (i >= 0 && i < (int)s.syms.size()) ? string(s.syms[(size_t)i].name) : string(); }
inline bool SymbolSelect(const string& n, bool sel) { (void)sel; return sim::sym(n) != nullptr; }
inline double SymbolInfoDouble(const string& n, ENUM_SYMBOL_INFO_DOUBLE p)
{
   sim::Symbol* s = sim::sym(n); if(!s) return 0.0;
   switch(p)
   {
      case SYMBOL_BID: return s->bid();
      case SYMBOL_ASK: return s->ask();
      case SYMBOL_POINT: return s->point;
      case SYMBOL_TRADE_TICK_VALUE: case SYMBOL_TRADE_TICK_VALUE_PROFIT: case SYMBOL_TRADE_TICK_VALUE_LOSS: return s->tick_value;
      case SYMBOL_TRADE_TICK_SIZE: return s->tick_size;
      case SYMBOL_TRADE_CONTRACT_SIZE: return s->contract;
      case SYMBOL_VOLUME_MIN: return s->vmin;
      case SYMBOL_VOLUME_MAX: return s->vmax;
      case SYMBOL_VOLUME_STEP: return s->vstep;
   }
   return 0.0;
}
inline long SymbolInfoInteger(const string& n, ENUM_SYMBOL_INFO_INTEGER p)
{
   sim::Symbol* s = sim::sym(n); if(!s) return 0;
   switch(p)
   {
      case SYMBOL_DIGITS: return s->digits;
      case SYMBOL_TRADE_STOPS_LEVEL: return s->stops;
      case SYMBOL_TRADE_MODE: return s->tradeable ? SYMBOL_TRADE_MODE_FULL : SYMBOL_TRADE_MODE_DISABLED;
      case SYMBOL_SPREAD: return (long)std::round((s->ask() - s->bid()) / s->point);
      default: return 0;
   }
}
inline int CopyRates(const string& n, ENUM_TIMEFRAMES tf, int start_pos, int count, MqlArr<MqlRates>& out)
{
   sim::Symbol* s = sim::sym(n); if(!s || count <= 0 || start_pos < 0) return -1;
   if(tf == PERIOD_M1)
   {
      if(s->cur < 0) return -1;
      long long last = s->cur - start_pos; if(last < 0) return -1;
      long long first = std::max(0LL, last - count + 1);
      out.v.assign(s->m1.begin() + first, s->m1.begin() + last + 1);
      if(start_pos == 0 && s->tick) { MqlRates& b = out.v.back(); b.high = b.low = b.close = b.open; }
      return out.size();
   }
   sim::Series* se = sim::series(*s, tf); if(!se || !se->started) return -1;
   long long last = (long long)se->cur - start_pos; if(last < 0) return -1;
   long long first = std::max(0LL, last - count + 1);
   out.v.assign(se->bars.begin() + first, se->bars.begin() + last + 1);
   if(start_pos == 0) out.v.back() = sim::forming(*s, *se, se->cur);
   return out.size();
}
inline int CopyRates(const string& n, ENUM_TIMEFRAMES tf, datetime from, datetime to, MqlArr<MqlRates>& out)
{
   sim::Symbol* s = sim::sym(n); if(!s) return -1;
   out.v.clear();
   if(tf == PERIOD_M1)
   {
      if(s->cur < 0) return -1;
      auto a = std::lower_bound(s->m1.begin(), s->m1.begin() + s->cur + 1, from, [](const MqlRates& r, datetime t) { return r.time < t; });
      for(auto it = a; it != s->m1.begin() + s->cur + 1 && it->time <= to; ++it) out.v.push_back(*it);
      if(!out.v.empty() && out.v.back().time == sim::S().now) { MqlRates& b = out.v.back(); b.high = b.low = b.close = b.open; }
      return out.size();
   }
   sim::Series* se = sim::series(*s, tf); if(!se || !se->started) return -1;
   for(size_t k = 0; k <= se->cur; k++)
      if(se->bars[k].time >= from && se->bars[k].time <= to) out.v.push_back(k == se->cur ? sim::forming(*s, *se, k) : se->bars[k]);
   return out.size();
}
inline datetime iTime(const string& n, ENUM_TIMEFRAMES tf, int shift)
{
   sim::Symbol* s = sim::sym(n); if(!s) return 0;
   if(tf == PERIOD_M1) { long long k = s->cur - shift; return k >= 0 ? s->m1[(size_t)k].time : 0; }
   sim::Series* se = sim::series(*s, tf); if(!se || !se->started) return 0;
   long long k = (long long)se->cur - shift; return k >= 0 ? se->bars[(size_t)k].time : 0;
}
inline double iClose(const string& n, ENUM_TIMEFRAMES tf, int shift)
{
   sim::Symbol* s = sim::sym(n); if(!s) return 0;
   if(tf == PERIOD_M1) { long long k = s->cur - shift; if(k < 0) return 0; return (shift == 0 && s->tick) ? s->m1[(size_t)k].open : s->m1[(size_t)k].close; }
   sim::Series* se = sim::series(*s, tf); if(!se || !se->started) return 0;
   long long k = (long long)se->cur - shift; if(k < 0) return 0;
   return shift == 0 ? sim::forming(*s, *se, (size_t)k).close : se->bars[(size_t)k].close;
}
inline int iMA(const string& n, ENUM_TIMEFRAMES tf, int period, int shift, ENUM_MA_METHOD m, ENUM_APPLIED_PRICE p)
{
   (void)shift;
   int si = sim::sym_index(n);
   if(si < 0 || m != MODE_EMA || p != PRICE_CLOSE || period <= 0) return INVALID_HANDLE;
   sim::Indicator ind; ind.sym = si; ind.tfmin = sim::tf_minutes(tf); ind.period = period;
   sim::S().ind.push_back(ind);
   return (int)sim::S().ind.size() - 1;
}
inline bool IndicatorRelease(int h) { (void)h; return true; }
inline int sim_copy_ema(int h, int buf, int start, int count, std::vector<double>& out)
{
   auto& st = sim::S();
   if(h < 0 || h >= (int)st.ind.size() || buf != 0 || count <= 0) return -1;
   sim::Indicator& ind = st.ind[(size_t)h];
   sim::Symbol& s = st.syms[(size_t)ind.sym];
   ENUM_TIMEFRAMES tf = ind.tfmin == 5 ? PERIOD_M5 : (ind.tfmin == 15 ? PERIOD_M15 : (ind.tfmin == 60 ? PERIOD_H1 : PERIOD_H4));
   sim::Series* se = sim::series(s, tf); if(!se || !se->started) return -1;
   if(ind.ema.empty())
   {   // EMA come l'indicatore di MetaTrader: primo valore = primo prezzo
      double k = 2.0 / (1.0 + ind.period); ind.ema.resize(se->bars.size());
      for(size_t i = 0; i < se->bars.size(); i++) ind.ema[i] = i == 0 ? se->bars[0].close : se->bars[i].close * k + ind.ema[i - 1] * (1 - k);
   }
   long long last = (long long)se->cur - start; if(last < 0) return -1;
   long long first = last - count + 1; if(first < 0) return -1;
   out.assign(ind.ema.begin() + first, ind.ema.begin() + last + 1);
   if(start == 0)
   {
      double k = 2.0 / (1.0 + ind.period), c = sim::forming(s, *se, se->cur).close;
      out.back() = se->cur == 0 ? c : c * k + ind.ema[se->cur - 1] * (1 - k);
   }
   return (int)out.size();
}
inline int CopyBuffer(int h, int buf, int start, int count, MqlArr<double>& out) { int n = sim_copy_ema(h, buf, start, count, out.v); if(n < 0) out.v.clear(); return n; }
template<size_t N> int CopyBuffer(int h, int buf, int start, int count, double (&out)[N])
{
   if((size_t)count > N) mql_fatal("CopyBuffer: array statico troppo piccolo", count, (long long)N);
   std::vector<double> v; int n = sim_copy_ema(h, buf, start, count, v);
   for(int i = 0; i < n; i++) out[i] = v[(size_t)i];
   return n;
}
inline bool OrderCalcMargin(ENUM_ORDER_TYPE t, const string& n, double vol, double price, double& margin)
{
   (void)t; sim::Symbol* s = sim::sym(n); if(!s) return false;
   margin = sim::margin_of(*s, vol, price); return true;
}

//==================================================================== API: posizioni e storico
inline int PositionsTotal() { return (int)sim::S().pos.size(); }
inline ulong PositionGetTicket(int i)
{
   auto& st = sim::S();
   if(i < 0 || i >= (int)st.pos.size()) { st.psel = -1; return 0; }
   st.psel = i; return st.pos[(size_t)i].ticket;
}
inline bool PositionSelectByTicket(ulong t) { long long i = sim::find_pos(t); sim::S().psel = i; return i >= 0; }
inline const sim::Position* sim_selpos() { auto& st = sim::S(); return (st.psel >= 0 && st.psel < (long long)st.pos.size()) ? &st.pos[(size_t)st.psel] : nullptr; }
inline long PositionGetInteger(ENUM_POSITION_PROPERTY_INTEGER p)
{
   const sim::Position* q = sim_selpos(); if(!q) return 0;
   switch(p)
   {
      case POSITION_TICKET: case POSITION_IDENTIFIER: return (long)q->ticket;
      case POSITION_TIME: return (long)q->time;
      case POSITION_TYPE: return q->type;
      case POSITION_MAGIC: return q->magic;
      default: return 0;
   }
}
inline double PositionGetDouble(ENUM_POSITION_PROPERTY_DOUBLE p)
{
   const sim::Position* q = sim_selpos(); if(!q) return 0;
   sim::Symbol* s = sim::sym(q->sym);
   switch(p)
   {
      case POSITION_VOLUME: return q->vol;
      case POSITION_PRICE_OPEN: return q->open;
      case POSITION_SL: return q->sl;
      case POSITION_TP: return q->tp;
      case POSITION_PRICE_CURRENT: return q->type == 0 ? s->bid() : s->ask();
      case POSITION_PROFIT: return sim::pos_profit(*s, *q);
      default: return 0;
   }
}
inline string PositionGetString(ENUM_POSITION_PROPERTY_STRING p)
{
   const sim::Position* q = sim_selpos(); if(!q) return string();
   return p == POSITION_SYMBOL ? string(q->sym) : string(q->comment);
}
inline bool HistorySelect(datetime from, datetime to)
{
   auto& st = sim::S();
   auto lo = std::lower_bound(st.deals.begin(), st.deals.end(), from, [](const sim::Deal& d, datetime t) { return d.time < t; });
   auto hi = std::upper_bound(st.deals.begin(), st.deals.end(), to, [](datetime t, const sim::Deal& d) { return t < d.time; });
   st.hsel_a = (size_t)(lo - st.deals.begin()); st.hsel_b = (size_t)(hi - st.deals.begin());
   return true;
}
inline int HistoryDealsTotal() { auto& st = sim::S(); return (int)(st.hsel_b - st.hsel_a); }
inline ulong HistoryDealGetTicket(int i) { auto& st = sim::S(); if(i < 0 || st.hsel_a + (size_t)i >= st.hsel_b) return 0; return st.deals[st.hsel_a + (size_t)i].ticket; }
inline const sim::Deal* sim_deal(ulong t)
{
   auto& st = sim::S();
   auto it = std::lower_bound(st.deals.begin(), st.deals.end(), t, [](const sim::Deal& d, ulong x) { return d.ticket < x; });
   return (it != st.deals.end() && it->ticket == t) ? &*it : nullptr;
}
inline long HistoryDealGetInteger(ulong t, ENUM_DEAL_PROPERTY_INTEGER p)
{
   const sim::Deal* d = sim_deal(t); if(!d) return 0;
   switch(p)
   {
      case DEAL_TICKET: return (long)d->ticket;
      case DEAL_ORDER: return (long)d->order;
      case DEAL_TIME: return (long)d->time;
      case DEAL_TYPE: return d->type;
      case DEAL_ENTRY: return d->entry;
      case DEAL_MAGIC: return d->magic;
      case DEAL_REASON: return d->reason;
      case DEAL_POSITION_ID: return (long)d->pos;
      default: return 0;
   }
}
inline double HistoryDealGetDouble(ulong t, ENUM_DEAL_PROPERTY_DOUBLE p)
{
   const sim::Deal* d = sim_deal(t); if(!d) return 0;
   switch(p)
   {
      case DEAL_VOLUME: return d->volume;
      case DEAL_PRICE: return d->price;
      case DEAL_COMMISSION: return d->commission;
      case DEAL_SWAP: return d->swap;
      case DEAL_PROFIT: return d->profit;
      default: return 0;
   }
}

//==================================================================== API: variabili globali
inline bool GlobalVariableCheck(const string& n) { return sim::S().gv.count(n) > 0; }
inline double GlobalVariableGet(const string& n) { auto& g = sim::S().gv; auto it = g.find(n); return it == g.end() ? 0.0 : it->second; }
inline datetime GlobalVariableSet(const string& n, double v)
{
   if(n.size() > 63) mql_fatal("nome di variabile globale oltre 63 caratteri", (long long)n.size());
   sim::S().gv[n] = v; return sim::S().now;
}
inline bool GlobalVariableDel(const string& n) { return sim::S().gv.erase(n) > 0; }
inline int GlobalVariablesDeleteAll(const string& prefix = string(), datetime limit = 0)
{
   (void)limit; auto& g = sim::S().gv; int n = 0;
   for(auto it = g.begin(); it != g.end();) { if(it->first.compare(0, prefix.size(), prefix) == 0) { it = g.erase(it); n++; } else ++it; }
   return n;
}
inline bool GlobalVariablesFlush() { return true; }
inline datetime TimeLocal() { return sim::S().now; }
inline long ChartID() { return sim::S().chart_id; }
inline int GlobalVariablesTotal() { return (int)sim::S().gv.size(); }
inline string GlobalVariableName(int i) { auto& g = sim::S().gv; if(i < 0 || i >= (int)g.size()) return string(); auto it = g.begin(); std::advance(it, i); return string(it->first); }

//==================================================================== API: file
inline int FileOpen(const string& name, int flags, short delim = '\t', uint codepage = 0)
{
   (void)codepage; auto& st = sim::S();
   std::string path = ((flags & FILE_COMMON) ? st.common_dir : st.files_dir) + "/" + name.str();
   const char* mode = (flags & FILE_WRITE) ? ((flags & FILE_READ) ? "a+" : "w") : "r";
   std::FILE* f = std::fopen(path.c_str(), mode);
   if(!f) { st.last_error = 5004; return INVALID_HANDLE; }
   sim::FileH h; h.f = f; h.flags = flags; h.delim = (char)delim; h.path = path;
   int id = st.next_file++; st.files[id] = h; return id;
}
inline void FileClose(int h) { auto& st = sim::S(); auto it = st.files.find(h); if(it != st.files.end()) { std::fclose(it->second.f); st.files.erase(it); } }
inline bool FileSeek(int h, long off, int origin) { auto& st = sim::S(); auto it = st.files.find(h); if(it == st.files.end()) return false; return std::fseek(it->second.f, off, origin) == 0; }
inline bool FileIsEnding(int h)
{
   auto& st = sim::S(); auto it = st.files.find(h); if(it == st.files.end()) return true;
   int c = std::fgetc(it->second.f); if(c == EOF) return true; std::ungetc(c, it->second.f); return false;
}
inline string FileReadString(int h, int len = -1)
{
   (void)len; auto& st = sim::S(); auto it = st.files.find(h); if(it == st.files.end()) return string();
   std::FILE* f = it->second.f; std::string r; int c;
   while((c = std::fgetc(f)) != EOF)
   {
      if(c == it->second.delim) break;
      if(c == '\r') { int d = std::fgetc(f); if(d != '\n' && d != EOF) std::ungetc(d, f); break; }
      if(c == '\n') break;
      r += (char)c;
   }
   return string(r);
}
template<class... A> uint FileWrite(int h, const A&... a)
{
   auto& st = sim::S(); auto it = st.files.find(h); if(it == st.files.end()) return 0;
   std::string line; bool first = true;
   ((line += (first ? "" : std::string(1, it->second.delim)) + sim_tostr(a), first = false), ...);
   line += "\r\n";
   std::fwrite(line.data(), 1, line.size(), it->second.f);
   return (uint)line.size();
}

//==================================================================== API: calendario e web (non disponibili nel tester)
template<class C> int CalendarValueHistory(MqlArr<MqlCalendarValue>& v, datetime from, datetime to = 0, C country = C(), const string& currency = string())
{
   (void)country; v.v.clear(); auto& s = sim::S();
   for(size_t i = 0; i < s.cal_vals.size(); i++) if(s.cal_vals[i].time >= from && (to == 0 || s.cal_vals[i].time <= to) && (currency.empty() || s.cal_cur[i] == currency)) v.v.push_back(s.cal_vals[i]);
   return v.size();
}
inline bool CalendarEventById(ulong id, MqlCalendarEvent& ev)
{
   for(auto& e : sim::S().cal_evs) if(e.id == id) { ev = e; return true; }
   ev = MqlCalendarEvent(); return false;
}
inline int WebRequest(const string& method, const string& url, const string& headers, int timeout, const MqlArr<char>& data, MqlArr<char>& result, string& result_headers)
{
   (void)method; (void)url; (void)headers; (void)timeout; (void)data; result_headers = string(); auto& s = sim::S();
   if(s.web_json.empty()) { result.v.clear(); s.last_error = 4014; return -1; }
   result.v.assign(s.web_json.begin(), s.web_json.end()); return 200;
}

//==================================================================== API: oggetti grafici (memorizzati, non disegnati)
inline int ObjectFind(long chart, const string& name) { (void)chart; return sim::S().obj_i.count(name) ? 0 : -1; }
inline bool ObjectCreate(long chart, const string& name, ENUM_OBJECT type, int sub, datetime t1, double p1) { (void)chart; (void)type; (void)sub; (void)t1; (void)p1; sim::S().obj_i[name]; sim::S().obj_s[name]; return true; }
inline bool ObjectSetInteger(long chart, const string& name, ENUM_OBJECT_PROPERTY_INTEGER p, long long v) { (void)chart; sim::S().obj_i[name][(int)p] = v; return true; }
inline bool ObjectSetString(long chart, const string& name, ENUM_OBJECT_PROPERTY_STRING p, const string& v) { (void)chart; sim::S().obj_s[name][(int)p] = v; return true; }
inline string ObjectGetString(long chart, const string& name, ENUM_OBJECT_PROPERTY_STRING p) { (void)chart; auto& m = sim::S().obj_s[name]; auto it = m.find((int)p); return it == m.end() ? string() : string(it->second); }
inline int ObjectsDeleteAll(long chart, const string& prefix, int sub = -1, int type = -1)
{
   (void)chart; (void)sub; (void)type; auto& st = sim::S(); int n = 0;
   for(auto it = st.obj_i.begin(); it != st.obj_i.end();) { if(it->first.compare(0, prefix.size(), prefix) == 0) { st.obj_s.erase(it->first); it = st.obj_i.erase(it); n++; } else ++it; }
   return n;
}
inline void ChartRedraw(long chart = 0) { (void)chart; }

//==================================================================== CTrade (stesse firme della libreria standard)
class CTrade
{
   ulong m_magic = 0, m_deviation = 10;
   MqlTradeResult m_result{};
public:
   void SetExpertMagicNumber(const ulong magic) { m_magic = magic; }
   void SetDeviationInPoints(const ulong deviation) { m_deviation = deviation; }
   bool SetTypeFillingBySymbol(const string& symbol) { return sim::sym(symbol) != nullptr; }
   bool Buy(const double volume, const string& symbol = string(), double price = 0.0, const double sl = 0.0, const double tp = 0.0, const string& comment = string()) { return Open(0, volume, symbol, price, sl, tp, comment); }
   bool Sell(const double volume, const string& symbol = string(), double price = 0.0, const double sl = 0.0, const double tp = 0.0, const string& comment = string()) { return Open(1, volume, symbol, price, sl, tp, comment); }
   bool PositionClose(const ulong ticket, const ulong deviation = ULONG_MAX)
   {
      (void)deviation; m_result = MqlTradeResult(); double px = 0;
      m_result.retcode = sim::close_position(ticket, px); m_result.price = px;
      return m_result.retcode == TRADE_RETCODE_DONE;
   }
   bool PositionModify(const ulong ticket, const double sl, const double tp)
   {
      m_result = MqlTradeResult(); m_result.retcode = sim::modify_position(ticket, sl, tp);
      return m_result.retcode == TRADE_RETCODE_DONE;
   }
   uint ResultRetcode() const { return m_result.retcode; }
   string ResultRetcodeDescription() const { return string("retcode ") + IntegerToString(m_result.retcode); }
   ulong ResultOrder() const { return m_result.order; }
   ulong ResultDeal() const { return m_result.deal; }
   double ResultPrice() const { return m_result.price; }
private:
   bool Open(int type, double volume, const string& symbol, double price, double sl, double tp, const string& comment)
   {
      (void)price; m_result = MqlTradeResult(); ulong t = 0; double px = 0;
      m_result.retcode = sim::open_position(symbol, type, volume, sl, tp, (long)m_magic, comment, t, px);
      if(m_result.retcode == TRADE_RETCODE_DONE) { m_result.order = t; m_result.deal = t; m_result.price = px; m_result.volume = volume; }
      return m_result.retcode == TRADE_RETCODE_DONE;   // come CTrade: false se il server rifiuta
   }
};
