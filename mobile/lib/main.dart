import 'dart:convert';
import 'dart:math' as math;
import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:local_auth/local_auth.dart';
import 'api.dart';
import 'studio.dart';
import 'risk_controls.dart';
void main() => runApp(const TradeMind());
const words = {
  'en':['Dashboard','Research','AI Assistant','Design Studio','Security','SIMULATED DEMO','Balance','Emergency stop','Analyze','Login','Register'],
  'ckb':['سەرەکی','توێژینەوە','یاریدەدەری زیرەک','ستۆدیۆی دیزاین','ئاسایش','هەژماری تاقیکردنەوە','باڵانس','وەستاندنی فریاکەوتن','شیکردنەوە','چوونەژوورەوە','تۆمارکردن'],
  'ar':['الرئيسية','البحث','مساعد الذكاء','استوديو التصميم','الأمان','حساب تجريبي','الرصيد','إيقاف طارئ','تحليل','دخول','تسجيل'],
};
class TradeMind extends StatefulWidget {
  const TradeMind({super.key});
  @override State<TradeMind> createState()=>_TradeMindState();
}
class _TradeMindState extends State<TradeMind> {
  String language='en';
  @override Widget build(BuildContext context)=>MaterialApp(
    title:'TradeMind AI OS',debugShowCheckedModeBanner:false,
    supportedLocales:const [Locale('en'),Locale('ar')],
    localizationsDelegates:GlobalMaterialLocalizations.delegates,
    locale:Locale(language=='ckb'?'ar':language),
    theme:ThemeData(brightness:Brightness.dark,useMaterial3:true,scaffoldBackgroundColor:const Color(0xff080d18),colorScheme:ColorScheme.fromSeed(seedColor:const Color(0xff45e0c1),brightness:Brightness.dark),cardTheme:const CardThemeData(color:Color(0xff121d30))),
    builder:(context,child)=>Directionality(textDirection:language=='en'?TextDirection.ltr:TextDirection.rtl,child:child!),
    home:Shell(language:language,onLanguage:(v)=>setState(()=>language=v)),
  );
}
class Shell extends StatefulWidget {
  final String language; final ValueChanged<String> onLanguage;
  const Shell({super.key,required this.language,required this.onLanguage});
  @override State<Shell> createState()=>_ShellState();
}
class _ShellState extends State<Shell> {
  final api=Api(); final email=TextEditingController(),password=TextEditingController(),symbol=TextEditingController(text:'EUR/USD'),message=TextEditingController();
  int page=0; bool logged=false,busy=false; String? error; dynamic account,signal,research,performance; List<dynamic> bars=[],history=[]; final List<Map<String,String>> chat=[];
  List<String> get t=>words[widget.language]!;
  Future<void> run(Future<void> Function() fn) async {
    setState(() {busy=true;error=null;});
    try {await fn();} catch(e) {if(mounted) setState(()=>error=e.toString());}
    finally {if(mounted) setState(()=>busy=false);}
  }
  Future<void> refresh() async {
    final a=await api.call('/account'); final h=await api.call('/demo/history'); final p=await api.call('/performance');
    if(mounted) setState(() {account=a;history=h;performance=p;});
    final data=await api.call('/market?symbol=${Uri.encodeComponent(symbol.text)}');
    if(mounted) setState(()=>bars=data['candles']);
  }
  Future<void> auth(bool register) => run(() async {
    final data=await api.call('/auth/${register?'register':'login'}',body:{'email':email.text,'password':password.text});
    await api.saveTokens(data); password.clear(); setState(()=>logged=true); await refresh();
  });
  @override void dispose() {email.dispose();password.dispose();symbol.dispose();message.dispose();super.dispose();}
  Widget button(String label,VoidCallback action,{IconData? icon})=>Padding(padding:const EdgeInsets.all(4),child:FilledButton.icon(onPressed:busy?null:action,icon:Icon(icon??Icons.arrow_forward,size:18),label:Text(label)));
  Widget card(String title,Widget child)=>Card(child:Padding(padding:const EdgeInsets.all(18),child:Column(crossAxisAlignment:CrossAxisAlignment.start,children:[Text(title,style:const TextStyle(fontSize:17,fontWeight:FontWeight.w600)),const SizedBox(height:14),child])));
  Widget output(dynamic data)=>SelectableText(const JsonEncoder.withIndent('  ').convert(data),style:const TextStyle(fontSize:12,fontFamily:'monospace'));
  @override Widget build(BuildContext context)=>Scaffold(
    appBar:AppBar(title:const Text('TradeMind AI OS',style:TextStyle(fontWeight:FontWeight.bold)),actions:[DropdownButton<String>(value:widget.language,items:const [DropdownMenuItem(value:'en',child:Text('EN')),DropdownMenuItem(value:'ckb',child:Text('کوردی')),DropdownMenuItem(value:'ar',child:Text('عربي'))],onChanged:(v)=>widget.onLanguage(v!))]),
    body:SafeArea(child:Column(children:[if(busy) const LinearProgressIndicator(),if(error!=null) MaterialBanner(content:Text(error!),actions:[TextButton(onPressed:()=>setState(()=>error=null),child:const Text('Dismiss'))]),Expanded(child:AnimatedSwitcher(duration:const Duration(milliseconds:250),child:!logged?login():content()))])),
    bottomNavigationBar:logged?NavigationBar(selectedIndex:page,onDestinationSelected:(i)=>setState(()=>page=i),destinations:List.generate(5,(i)=>NavigationDestination(icon:Icon([Icons.space_dashboard_outlined,Icons.query_stats,Icons.auto_awesome,Icons.palette_outlined,Icons.shield_outlined][i]),label:t[i]))):null,
  );
  Widget login()=>Center(child:ConstrainedBox(constraints:const BoxConstraints(maxWidth:420),child:ListView(shrinkWrap:true,padding:const EdgeInsets.all(24),children:[const Icon(Icons.auto_graph,size:72,color:Color(0xff45e0c1)),const Text('TradeMind',textAlign:TextAlign.center,style:TextStyle(fontSize:36,fontWeight:FontWeight.bold)),Text(t[5],textAlign:TextAlign.center),const SizedBox(height:30),TextField(controller:email,keyboardType:TextInputType.emailAddress,decoration:const InputDecoration(labelText:'Email')),TextField(controller:password,obscureText:true,decoration:const InputDecoration(labelText:'Password · 12+ characters')),button(t[9],()=>auth(false)),button(t[10],()=>auth(true))])));
  Widget content() {
    if(page==3) return Studio(api:api);
    return ListView(key:ValueKey(page),padding:const EdgeInsets.all(16),children:page==0?dashboard():page==1?researchPage():page==2?assistant():security());
  }
  List<Widget> dashboard()=>[
    Row(children:[Chip(label:Text(t[5]),avatar:const Icon(Icons.science,size:16)),const Spacer(),IconButton(onPressed:()=>run(refresh),icon:const Icon(Icons.refresh))]),
    card(t[6],Column(crossAxisAlignment:CrossAxisAlignment.start,children:[Text('\$${account?['balance']??'—'}',style:const TextStyle(fontSize:34,fontWeight:FontWeight.bold)),Text(account?['halted']==true?'Trading suspended':'Independent simulator · no broker execution')])),
    if(performance!=null)card('Demo performance',Column(crossAxisAlignment:CrossAxisAlignment.start,children:[Text('Net P&L: ${performance['metrics']['net_pnl']} · Reserved: ${performance['reserved']}'),SizedBox(height:100,child:CustomPaint(painter:EquityPainter(List<num>.from(performance['equity'])),size:const Size(double.infinity,100))),output(performance['metrics'])])),
    card('Market · Twelve Data',Column(children:[TextField(controller:symbol,decoration:const InputDecoration(labelText:'Instrument')),SizedBox(height:210,child:bars.isEmpty?const Center(child:Text('Configure market provider to load candles')):CustomPaint(painter:CandlesPainter(bars),size:const Size(double.infinity,210))),button(t[8],()=>run(() async {final s=await api.call('/signals?symbol=${Uri.encodeComponent(symbol.text)}');setState(()=>signal=s);await refresh();}))])),
    if(signal!=null) card('AI signal · deterministic indicators',Column(crossAxisAlignment:CrossAxisAlignment.start,children:[Text(signal['recommendation'],style:const TextStyle(fontSize:28,color:Color(0xff45e0c1))),Text(signal['confidence_note']),output(signal['indicators']),Wrap(children:['BUY','SELL'].map((side)=>button('Demo $side · \$50',()=>run(()async {await api.call('/demo/orders',body:{'symbol':symbol.text,'side':side,'stake':50,'expiry':300,'idempotency_key':'mobile-${DateTime.now().microsecondsSinceEpoch}'});await refresh();}))).toList())])),
    button('Enable autonomous demo · $50 stakes',()=>run(() async {await api.call('/demo/automation',body:{'enabled':true,'symbol':symbol.text});})),
    button('Disable autonomous demo',()=>run(() async {await api.call('/demo/automation',body:{'enabled':false,'symbol':symbol.text});})),
    button(t[7],()=>run(() async {await api.call('/risk/stop',body:{});await refresh();}),icon:Icons.stop_circle),
    card('Simulated history',Column(children:[button('Settle expired positions',()=>run(()async {await api.call('/demo/settle',body:{});await refresh();})),if(history.isEmpty)const Text('No simulated transactions'),...history.map((h)=>ListTile(title:Text('${h['side']} ${h['symbol']} · ${h['status']}'),subtitle:Text('SIMULATED · entry ${h['entry']}'),trailing:Text(h['pnl']??'Pending')))])),
  ];
  List<Widget> researchPage()=>[card('Strategy research',Column(crossAxisAlignment:CrossAxisAlignment.start,children:[const Text('EMA momentum v1 · chronological next-bar fills, costs and walk-forward validation. Historical performance is not a forecast.'),button('Run historical validation',()=>run(()async {final r=await api.call('/research/backtest?symbol=${Uri.encodeComponent(symbol.text)}',body:{});setState(()=>research=r);})),if(research!=null)output(research)]))];
  List<Widget> assistant()=>[const Text('Gemini explanations · cannot execute transactions'),...chat.map((m)=>card(m['role']!,SelectableText(m['text']!))),TextField(controller:message,maxLines:3,decoration:const InputDecoration(labelText:'Ask about your demo account')),button('Send',()=>run(()async {final text=message.text;if(text.trim().isEmpty)return;setState(()=>chat.add({'role':'You','text':text}));message.clear();final r=await api.call('/assistant',body:{'message':text});setState(()=>chat.add({'role':'TradeMind','text':r['reply']}));}))];
  List<Widget> security()=>[card('Risk settings',RiskControls(api:api)),card(t[4],Column(crossAxisAlignment:CrossAxisAlignment.start,children:[const Text('Real-money execution is disabled. Provider keys stay on the server. Tokens use device secure storage.'),button('Verify device biometrics',()=>run(()async {final ok=await LocalAuthentication().authenticate(localizedReason:'Unlock TradeMind',options:const AuthenticationOptions(biometricOnly:true));if(!ok)throw Exception('Biometric verification failed');})),button('Revoke sessions and sign out',()=>run(()async {await api.call('/auth/logout',body:{});await api.storage.deleteAll();setState(()=>logged=false);}))]))];
}
class CandlesPainter extends CustomPainter {
  final List<dynamic> candles; CandlesPainter(this.candles);
  @override void paint(Canvas canvas,Size size) {
    final data=candles.skip(math.max(0,candles.length-55)).toList();if(data.isEmpty)return;
    final hi=data.map((c)=>(c['high'] as num).toDouble()).reduce(math.max),lo=data.map((c)=>(c['low'] as num).toDouble()).reduce(math.min);
    double y(num v)=>size.height-10-(v-lo)/math.max(hi-lo,.000001)*(size.height-20);
    final step=size.width/data.length;
    for(var i=0;i<data.length;i++){final c=data[i];final p=Paint()..color=c['close']>=c['open']?const Color(0xff45e0c1):const Color(0xffff667e);final x=step*(i+.5);canvas.drawLine(Offset(x,y(c['high'])),Offset(x,y(c['low'])),p);canvas.drawRect(Rect.fromLTRB(x-step*.3,math.min(y(c['open']),y(c['close'])),x+step*.3,math.max(y(c['open']),y(c['close']))+1),p);}
  }
  @override bool shouldRepaint(CandlesPainter old)=>true;
}

class EquityPainter extends CustomPainter {
 final List<num> values;EquityPainter(this.values);
 @override void paint(Canvas canvas,Size size){if(values.length<2)return;final hi=values.reduce(math.max).toDouble(),lo=values.reduce(math.min).toDouble();final path=Path();for(var i=0;i<values.length;i++){final x=i/(values.length-1)*size.width,y=size.height-8-(values[i]-lo)/math.max(hi-lo,.01)*(size.height-16);if(i==0){path.moveTo(x,y);}else{path.lineTo(x,y);}}canvas.drawPath(path,Paint()..color=const Color(0xff45e0c1)..strokeWidth=2..style=PaintingStyle.stroke);}
 @override bool shouldRepaint(EquityPainter old)=>true;
}
